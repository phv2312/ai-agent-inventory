from datetime import datetime

from pydantic import BaseModel, Field


class ContentBlockResponse(BaseModel):
    id: str
    type: str
    order: int
    status: str
    text: str | None = None
    title: str | None = None
    loading_messages: list[str] = Field(default_factory=list)
    widget_code: str | None = None
    error_message: str | None = None


class ConversationCreate(BaseModel):
    title: str = ""


class ConversationUpdate(BaseModel):
    title: str = Field(min_length=0, max_length=255)


class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    content_blocks: list[ContentBlockResponse] = Field(default_factory=list)
    mapping_evidence: dict[str, str] | None = None
    created_at: datetime
