from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class IndexStatusResponse(StrEnum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class ReferenceResponse(BaseModel):
    id: str
    collection_id: str
    filename: str
    doc_name: str
    content_type: str
    status: IndexStatusResponse
    error_message: str | None = None
    metadata: dict[str, object] | None = None
    created_at: datetime
    updated_at: datetime


class ReferenceChunkPreview(BaseModel):
    id: str
    ordinal: int
    page_number: int | None
    preview: str


class ReferenceChunksResponse(BaseModel):
    total: int
    items: list[ReferenceChunkPreview]


class ReferenceChunkDetail(BaseModel):
    id: str
    document_id: str
    document_name: str
    page_number: int | None
    text: str
