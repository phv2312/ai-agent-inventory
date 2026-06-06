"""Data models for the agentic RAG Gradio demo."""

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class IndexedFile(BaseModel):
    """Metadata for an indexed document."""

    fileid: str
    name: str
    size_bytes: int
    token_count: int
    loader: str = "PDFExtractor"
    date_created: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
    )
    filepath: str = ""

    @property
    def size_label(self) -> str:
        if self.size_bytes < 1024:
            return f"{self.size_bytes}B"
        if self.size_bytes < 1024 * 1024:
            return f"{self.size_bytes // 1024}KB"
        return f"{self.size_bytes // (1024 * 1024)}MB"

    @property
    def token_label(self) -> str:
        if self.token_count < 1000:
            return str(self.token_count)
        return f"{self.token_count // 1000}K"

    def as_row(self) -> list[str]:
        return [
            self.fileid,
            self.name,
            self.size_label,
            self.token_label,
            self.loader,
            self.date_created.strftime("%Y-%m-%d %H:%M:%S"),
        ]


class Conversation(BaseModel):
    """In-memory chat session."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = "New conversation"
    history: list[dict[str, str]] = Field(default_factory=list)
    selected_file_ids: list[str] = Field(default_factory=list)
    search_all: bool = True
