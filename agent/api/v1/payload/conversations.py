from datetime import datetime

from pydantic import BaseModel, Field


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
    mapping_evidence: dict[str, str] | None = None
    created_at: datetime
