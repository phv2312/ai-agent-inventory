import re

from pydantic import BaseModel, Field


class StreamChatItem(BaseModel):
    idx: int = 0
    role: str = "assistant"
    content: str


class StreamErrorData(BaseModel):
    code: str
    message: str


class NameSuggestionData(BaseModel):
    name: str


class BlockOpenData(BaseModel):
    type: str
    order: int
    module: str | None = None
    title: str | None = None
    loading_messages: list[str] = Field(default_factory=list)


class BlockDeltaData(BaseModel):
    order: int
    content: str


class BlockCloseData(BaseModel):
    order: int
    status: str
    error_message: str | None = None


class TokenUsageData(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


CITATION_INDEX_PATTERN = re.compile(r"\[\s*(\d+)\s*\]")

UNTITLED_CONVERSATION_TITLES = frozenset({"", "new conversation"})


def is_untitled_conversation(title: str) -> bool:
    return title.strip().lower() in UNTITLED_CONVERSATION_TITLES
