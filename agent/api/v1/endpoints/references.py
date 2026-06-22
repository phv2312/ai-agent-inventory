import json
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from agent.api.container import ApiContainer
from agent.api.exc.http import AppError
from agent.api.v1.deps.root import get_container, get_repos, get_settings
from agent.api.v1.payload.references import (
    IndexStatusResponse,
    ReferenceChunkItem,
    ReferenceChunksResponse,
    ReferenceResponse,
)
from agent.api.settings import ApiSettings
from agent.deps.models import VectorDBModel
from agent.db.models import IndexStatus
from agent.models.document import DocumentMetadata
from agent.repos.protocols import ReferenceRecord
from agent.api.container import Repositories
from agent.storages.config import AnchorFields
from agent.storages.reference_files import ReferenceFileStorage

router = APIRouter()

PDF_CONTENT_TYPES = {"application/pdf", "application/x-pdf"}


def _to_response(record: ReferenceRecord) -> ReferenceResponse:
    return ReferenceResponse(
        id=record.id,
        collection_id=record.collection_id,
        filename=record.filename,
        doc_name=record.doc_name,
        content_type=record.content_type,
        status=IndexStatusResponse(record.status.value),
        error_message=record.error_message,
        metadata=record.metadata_json,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.post(
    "/", response_model=ReferenceResponse, status_code=status.HTTP_202_ACCEPTED
)
async def upload_reference(
    settings: Annotated[ApiSettings, Depends(get_settings)],
    container: Annotated[ApiContainer, Depends(get_container)],
    collection_id: str = Form(...),
    reference: UploadFile = File(...),
    metadata: str | None = Form(default=None),
) -> ReferenceResponse:
    content_type = reference.content_type or ""
    filename = reference.filename or "upload.pdf"
    if content_type not in PDF_CONTENT_TYPES and not filename.lower().endswith(".pdf"):
        raise AppError(
            "UnsupportedMediaType",
            "Only PDF uploads are supported in v1",
            415,
        )

    raw = await reference.read()
    if len(raw) > settings.MAX_UPLOAD_BYTES:
        raise AppError(
            "ValidationError",
            f"File exceeds maximum size of {settings.MAX_UPLOAD_BYTES} bytes",
            422,
        )

    metadata_json: dict[str, object] | None = None
    doc_name = Path(filename).name
    if metadata:
        try:
            parsed = json.loads(metadata)
            if isinstance(parsed, dict):
                metadata_json = parsed
                if parsed.get("doc_name"):
                    doc_name = str(parsed["doc_name"])
        except json.JSONDecodeError as exc:
            raise AppError(
                "ValidationError", f"Invalid metadata JSON: {exc}", 422
            ) from exc

    async with container.session_factory() as session:
        repos = container.repos(session)
        collection = await repos.collections.get(collection_id)
        if collection is None:
            raise AppError("NotFound", f"Collection {collection_id} not found", 404)

        if await repos.references.doc_name_exists(collection_id, doc_name):
            raise AppError(
                "ValidationError",
                f"doc_name '{doc_name}' already exists in collection",
                422,
            )

        record = await repos.references.create(
            collection_id=collection_id,
            doc_name=doc_name,
            filename=filename,
            content_type=content_type or "application/pdf",
            file_path="",
            metadata_json=metadata_json,
        )

        storage = ReferenceFileStorage(container.references_dir)
        saved_path = storage.save_pdf(record.id, filename, raw)
        rel_path = f"references/{record.id}/{Path(filename).name}"
        updated = await repos.references.set_file_path(record.id, rel_path)
        if updated is None:
            raise AppError("NotFound", "Reference not found after create", 404)

        await session.commit()
        response = _to_response(updated)

    container.indexing_worker().schedule(updated.id, saved_path, collection_id)
    return response


@router.get("/{reference_id}", response_model=ReferenceResponse)
async def get_reference(
    reference_id: str,
    repos: Annotated[Repositories, Depends(get_repos)],
) -> ReferenceResponse:
    record = await repos.references.get(reference_id)
    if record is None:
        raise AppError("NotFound", f"Reference {reference_id} not found", 404)
    return _to_response(record)


@router.get("/{reference_id}/chunks", response_model=ReferenceChunksResponse)
async def list_reference_chunks(
    reference_id: str,
    repos: Annotated[Repositories, Depends(get_repos)],
    container: Annotated[ApiContainer, Depends(get_container)],
) -> ReferenceChunksResponse:
    record = await repos.references.get(reference_id)
    if record is None:
        raise AppError("NotFound", f"Reference {reference_id} not found", 404)
    if record.status != IndexStatus.completed:
        raise AppError(
            "ValidationError",
            f"Reference indexing not completed (status={record.status.value})",
            422,
        )

    milvus = container.agent.vectordbs.get(VectorDBModel.MILVUS)
    scored = await milvus.retrieve_by_filter({AnchorFields.FILE_ID: [reference_id]})
    items: list[ReferenceChunkItem] = []
    for scored_chunk in scored.root:
        meta: dict[str, object] = {
            "doc_name": record.doc_name,
            "reference_id": reference_id,
            "collection_id": record.collection_id,
        }
        if isinstance(scored_chunk.chunk.metadata, DocumentMetadata):
            meta["filename"] = scored_chunk.chunk.metadata.filename
            meta["page_idx"] = scored_chunk.chunk.metadata.pageidx
        items.append(
            ReferenceChunkItem(
                id=str(scored_chunk.chunk.chunk_id),
                text=scored_chunk.chunk.text,
                metadata=meta,
            )
        )
    return ReferenceChunksResponse(items=items)
