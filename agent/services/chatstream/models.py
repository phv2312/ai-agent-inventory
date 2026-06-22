import re

from pydantic import BaseModel


class StreamChatItem(BaseModel):
    idx: int = 0
    role: str = "assistant"
    content: str


class StreamErrorData(BaseModel):
    code: str
    message: str


class NameSuggestionData(BaseModel):
    name: str


class TokenUsageData(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


CITATION_INDEX_PATTERN = re.compile(r"\[\s*(\d+)\s*\]")

UNTITLED_CONVERSATION_TITLES = frozenset({"", "new conversation"})


def is_untitled_conversation(title: str) -> bool:
    return title.strip().lower() in UNTITLED_CONVERSATION_TITLES
