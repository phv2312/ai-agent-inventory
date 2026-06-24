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


class ReferenceChunkItem(BaseModel):
    id: str
    text: str
    metadata: dict[str, object]


class ReferenceChunksResponse(BaseModel):
    items: list[ReferenceChunkItem]
