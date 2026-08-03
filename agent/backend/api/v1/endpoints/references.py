import json
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status

from agent.backend.api.container import ApiContainer
from agent.backend.api.exc.http import AppError
from agent.backend.api.v1.deps.root import get_container, get_repos, get_settings
from agent.backend.api.v1.payload.references import (
    IndexStatusResponse,
    ReferenceChunkDetail,
    ReferenceChunkPreview,
    ReferenceChunksResponse,
    ReferenceResponse,
)
from agent.backend.api.settings import ApiSettings
from agent.backend.db.models import IndexStatus
from agent.backend.repos.protocols import ReferenceRecord
from agent.backend.api.container import Repositories
from agent.core.deps.models import VectorDBModel
from agent.core.models.document import DocumentMetadata, ScoredChunk
from agent.core.storages.config import AnchorFields
from agent.core.storages.files.exporter import ReferenceExporter

router = APIRouter()

PDF_CONTENT_TYPES = {"application/pdf", "application/x-pdf"}
CHUNK_PREVIEW_LENGTH = 240
DEFAULT_CHUNK_PAGE_SIZE = 50
MAX_CHUNK_PAGE_SIZE = 100


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

        safe_filename = Path(filename).name
        exporter = ReferenceExporter(record.id)
        source_key = exporter.source_key(safe_filename)
        saved_key = container.agent.storage.write_bytes(source_key, raw)
        updated = await repos.references.set_file_path(record.id, saved_key)
        if updated is None:
            raise AppError("NotFound", "Reference not found after create", 404)

        await session.commit()
        response = _to_response(updated)

    container.indexing_worker().schedule(
        updated.id,
        saved_key,
        safe_filename,
        collection_id,
    )
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


@router.delete(
    "/{reference_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_reference(
    reference_id: str,
    container: Annotated[ApiContainer, Depends(get_container)],
) -> Response:
    async with container.session_factory() as session:
        repos = container.repos(session)
        record = await repos.references.get(reference_id)
        if record is None:
            raise AppError("NotFound", f"Reference {reference_id} not found", 404)

        milvus = container.agent.vectordbs.get(VectorDBModel.MILVUS)
        await milvus.delete_by_filter({AnchorFields.FILE_ID: [reference_id]})

        deleted = await repos.references.delete(reference_id)
        if not deleted:
            raise AppError("NotFound", f"Reference {reference_id} not found", 404)
        await session.commit()

    container.agent.storage.delete_prefix(ReferenceExporter(reference_id).prefix)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{reference_id}/chunks", response_model=ReferenceChunksResponse)
async def list_reference_chunks(
    reference_id: str,
    repos: Annotated[Repositories, Depends(get_repos)],
    container: Annotated[ApiContainer, Depends(get_container)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=MAX_CHUNK_PAGE_SIZE)] = (
        DEFAULT_CHUNK_PAGE_SIZE
    ),
) -> ReferenceChunksResponse:
    await get_completed_reference(reference_id, repos)

    milvus = container.agent.vectordbs.get(VectorDBModel.MILVUS)
    scored = await milvus.retrieve_all_by_filter({AnchorFields.FILE_ID: [reference_id]})
    ordered = sorted(scored.root, key=chunk_preview_sort_key)
    return ReferenceChunksResponse(
        total=len(ordered),
        items=[
            to_chunk_preview(scored_chunk, ordinal=index)
            for index, scored_chunk in enumerate(
                ordered[offset : offset + limit], start=offset + 1
            )
        ],
    )


@router.get("/{reference_id}/chunks/{chunk_id}", response_model=ReferenceChunkDetail)
async def get_reference_chunk(
    reference_id: str,
    chunk_id: str,
    repos: Annotated[Repositories, Depends(get_repos)],
    container: Annotated[ApiContainer, Depends(get_container)],
) -> ReferenceChunkDetail:
    record = await get_completed_reference(reference_id, repos)
    milvus = container.agent.vectordbs.get(VectorDBModel.MILVUS)
    scored = await milvus.retrieve_by_filter(
        {AnchorFields.FILE_ID: [reference_id], AnchorFields.ID: [chunk_id]}, limit=1
    )
    if not scored.root:
        raise AppError("NotFound", f"Chunk {chunk_id} not found", 404)

    chunk = scored.root[0].chunk
    return ReferenceChunkDetail(
        id=str(chunk.chunk_id),
        document_id=reference_id,
        document_name=record.doc_name,
        page_number=chunk_page_number(scored.root[0]),
        text=chunk.text,
    )


async def get_completed_reference(
    reference_id: str, repos: Repositories
) -> ReferenceRecord:
    record = await repos.references.get(reference_id)
    if record is None:
        raise AppError("NotFound", f"Reference {reference_id} not found", 404)
    if record.status != IndexStatus.completed:
        raise AppError(
            "ValidationError",
            f"Reference indexing not completed (status={record.status.value})",
            422,
        )
    return record


def chunk_page_number(scored_chunk: ScoredChunk) -> int | None:
    if isinstance(scored_chunk.chunk.metadata, DocumentMetadata):
        return scored_chunk.chunk.metadata.pageidx
    return None


def chunk_preview_sort_key(scored_chunk: ScoredChunk) -> tuple[int, int, str]:
    page_number = chunk_page_number(scored_chunk)
    if page_number is None:
        return (1, 0, str(scored_chunk.chunk.chunk_id))
    return (0, -page_number, str(scored_chunk.chunk.chunk_id))


def to_chunk_preview(
    scored_chunk: ScoredChunk, *, ordinal: int
) -> ReferenceChunkPreview:
    text = scored_chunk.chunk.text.strip()
    preview = text[:CHUNK_PREVIEW_LENGTH]
    if len(text) > CHUNK_PREVIEW_LENGTH:
        preview = f"{preview.rstrip()}…"
    return ReferenceChunkPreview(
        id=str(scored_chunk.chunk.chunk_id),
        ordinal=ordinal,
        page_number=chunk_page_number(scored_chunk),
        preview=preview,
    )
