from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from agent.backend.api.exc.http import AppError
from agent.backend.api.v1.deps.root import get_repos, get_settings
from agent.backend.api.v1.payload.collections import (
    CollectionCreate,
    CollectionListResponse,
    CollectionResponse,
    CollectionUpdate,
)
from agent.backend.api.v1.payload.references import (
    IndexStatusResponse,
    ReferenceResponse,
)
from agent.backend.api.settings import ApiSettings
from agent.backend.api.container import Repositories
from agent.backend.repos.protocols import CollectionRecord, ReferenceRecord

router = APIRouter()


def _to_response(record: object) -> CollectionResponse:
    assert isinstance(record, CollectionRecord)
    return CollectionResponse(
        id=record.id,
        name=record.name,
        description=record.description,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.post(
    "/", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED
)
async def create_collection(
    body: CollectionCreate,
    repos: Annotated[Repositories, Depends(get_repos)],
) -> CollectionResponse:
    record = await repos.collections.create(body.name, body.description)
    return _to_response(record)


@router.get("/", response_model=CollectionListResponse)
async def list_collections(
    repos: Annotated[Repositories, Depends(get_repos)],
    settings: Annotated[ApiSettings, Depends(get_settings)],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> CollectionListResponse:
    items = await repos.collections.list(skip=skip, limit=limit)
    return CollectionListResponse(
        items=[_to_response(item) for item in items],
        skip=skip,
        limit=limit,
    )


@router.get("/{collection_id}", response_model=CollectionResponse)
async def get_collection(
    collection_id: str,
    repos: Annotated[Repositories, Depends(get_repos)],
) -> CollectionResponse:
    record = await repos.collections.get(collection_id)
    if record is None:
        raise AppError("NotFound", f"Collection {collection_id} not found", 404)
    return _to_response(record)


def _reference_response(record: ReferenceRecord) -> ReferenceResponse:
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


@router.get("/{collection_id}/references", response_model=list[ReferenceResponse])
async def list_collection_references(
    collection_id: str,
    repos: Annotated[Repositories, Depends(get_repos)],
) -> list[ReferenceResponse]:
    record = await repos.collections.get(collection_id)
    if record is None:
        raise AppError("NotFound", f"Collection {collection_id} not found", 404)
    refs = await repos.references.list_by_collection(collection_id)
    return [_reference_response(r) for r in refs]


@router.put("/{collection_id}", response_model=CollectionResponse)
async def update_collection(
    collection_id: str,
    body: CollectionUpdate,
    repos: Annotated[Repositories, Depends(get_repos)],
) -> CollectionResponse:
    record = await repos.collections.update(
        collection_id,
        name=body.name,
        description=body.description,
    )
    if record is None:
        raise AppError("NotFound", f"Collection {collection_id} not found", 404)
    return _to_response(record)


@router.delete(
    "/{collection_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response
)
async def delete_collection(
    collection_id: str,
    repos: Annotated[Repositories, Depends(get_repos)],
) -> Response:
    deleted = await repos.collections.delete(collection_id)
    if not deleted:
        raise AppError("NotFound", f"Collection {collection_id} not found", 404)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
