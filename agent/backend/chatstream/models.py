import re

from pydantic import BaseModel, Field

from agent.core.tools import AgentInterruption


class StreamChatItem(BaseModel):
    idx: int = 0
    role: str = "assistant"
    content: str


class StreamErrorData(BaseModel):
    code: str
    message: str


class NameSuggestionData(BaseModel):
    name: str


class InterruptionEventData(BaseModel):
    conversation_id: str
    version: int = Field(ge=1)
    interruptions: list[AgentInterruption] = Field(min_length=1)


CITATION_INDEX_PATTERN = re.compile(r"\[\s*(\d+)\s*\]")

UNTITLED_CONVERSATION_TITLES = frozenset({"", "new conversation"})


def is_untitled_conversation(title: str) -> bool:
    return title.strip().lower() in UNTITLED_CONVERSATION_TITLES
