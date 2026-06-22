from typing import Annotated

from fastapi import APIRouter, Depends, Query

from agent.api.container import ApiContainer, Repositories
from agent.api.exc.http import AppError
from agent.api.settings import ApiSettings
from agent.api.v1.deps.root import get_container, get_repos, get_settings
from agent.api.v1.docs.description import Descriptions
from agent.api.v1.payload.chunks import ChunkItemResponse, ChunksBatchResponse
from agent.citations.inline import apply_snippet_highlights
from agent.deps.models import VectorDBModel
from agent.models.document import DocumentMetadata, ScoredChunk
from agent.storages.config import AnchorFields

router = APIRouter()


@router.get(
    "/",
    response_model=ChunksBatchResponse,
    summary="Batch get chunks",
    description=Descriptions.BATCH_CHUNKS,
)
async def batch_get_chunks(
    repos: Annotated[Repositories, Depends(get_repos)],
    container: Annotated[ApiContainer, Depends(get_container)],
    settings: Annotated[ApiSettings, Depends(get_settings)],
    chunk_ids: Annotated[list[str], Query()],
    snippets: Annotated[list[str] | None, Query()] = None,
) -> ChunksBatchResponse:
    if not chunk_ids:
        raise AppError("ValidationError", "chunk_ids is required", 422)
    if len(chunk_ids) > settings.MAX_CHUNK_IDS:
        raise AppError(
            "ValidationError",
            f"At most {settings.MAX_CHUNK_IDS} chunk_ids allowed",
            422,
        )
    snippet_list = snippets or []
    if len(snippet_list) > settings.MAX_SNIPPETS:
        raise AppError(
            "ValidationError",
            f"At most {settings.MAX_SNIPPETS} snippets allowed",
            422,
        )

    milvus = container.agent.vectordbs.get(VectorDBModel.MILVUS)
    scored = await milvus.retrieve_by_filter({AnchorFields.ID: chunk_ids})
    by_id = {str(s.chunk.chunk_id): s for s in scored.root}

    mp_snippets: dict[str, list[str]] = {}
    if snippet_list:
        default_snippets = snippet_list
        for i, chunk_id in enumerate(chunk_ids):
            if len(snippet_list) == len(chunk_ids):
                mp_snippets[chunk_id] = [snippet_list[i]]
            else:
                mp_snippets[chunk_id] = list(default_snippets)

    highlighted = apply_snippet_highlights(list(by_id.values()), mp_snippets)
    highlighted_by_id = {str(s.chunk.chunk_id): s for s in highlighted}

    items: list[ChunkItemResponse] = []
    for chunk_id in chunk_ids:
        scored_chunk = highlighted_by_id.get(chunk_id) or by_id.get(chunk_id)
        if scored_chunk is None:
            items.append(
                ChunkItemResponse(
                    id=chunk_id,
                    text=None,
                    metadata=None,
                    status="not_found",
                    warnings=["chunk not found"],
                )
            )
            continue

        warnings: list[str] | None = None
        if snippet_list and chunk_id in mp_snippets:
            if "<mark" not in scored_chunk.chunk.text:
                warnings = ["snippet did not match chunk text"]

        meta = await _chunk_metadata(scored_chunk, repos)
        items.append(
            ChunkItemResponse(
                id=chunk_id,
                text=scored_chunk.chunk.text,
                metadata=meta,
                status="ok",
                warnings=warnings,
            )
        )

    return ChunksBatchResponse(items=items)


async def _chunk_metadata(
    scored: ScoredChunk, repos: Repositories
) -> dict[str, object]:
    meta: dict[str, object] = {}
    if isinstance(scored.chunk.metadata, DocumentMetadata):
        ref_id = scored.chunk.metadata.fileid
        meta = {
            "filename": scored.chunk.metadata.filename,
            "page_idx": scored.chunk.metadata.pageidx,
            "reference_id": ref_id,
        }
        ref = await repos.references.get(ref_id)
        if ref is not None:
            meta["doc_name"] = ref.doc_name
            meta["collection_id"] = ref.collection_id
    return meta
