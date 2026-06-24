"""Ordered assistant message content blocks (text + visual widgets)."""

from enum import StrEnum

from pydantic import BaseModel, Field


class ContentBlockType(StrEnum):
    TEXT = "text"
    VISUAL_WIDGET = "visual_widget"


class WidgetBlockStatus(StrEnum):
    STREAMING = "streaming"
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    ERROR = "error"


class ContentBlock(BaseModel):
    id: str
    type: ContentBlockType
    order: int
    status: WidgetBlockStatus
    module: str | None = None
    text: str | None = None
    title: str | None = None
    loading_messages: list[str] = Field(default_factory=list)
    widget_code: str | None = None
    error_message: str | None = None
