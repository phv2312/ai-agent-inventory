from enum import StrEnum, auto
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

from agent.models.messages import (
    AssistantMessage,
    MessageRole,
    UserMessage,
)


class WebSearchActionType(StrEnum):
    SEARCH = auto()
    OPEN_PAGE = auto()
    FIND = auto()


class WebSearchStatus(StrEnum):
    SEARCHING = auto()
    COMPLETED = auto()
    FAILED = auto()

    @property
    def icon(self) -> str:
        return {
            WebSearchStatus.SEARCHING: "🔍",
            WebSearchStatus.COMPLETED: "✅",
            WebSearchStatus.FAILED: "❌",
        }[self]


class StreamEventType(StrEnum):
    TEXT_DELTA = auto()
    TEXT_DONE = auto()

    FUNCTION_CALL_START = auto()
    FUNCTION_CALL_ARGS_DELTA = auto()
    FUNCTION_CALL_ARGS_DONE = auto()

    THINKING_DELTA = auto()
    THINKING_DONE = auto()

    MESSAGE_START = auto()
    MESSAGE_DONE = auto()

    ERROR = auto()


class FunctionType(StrEnum):
    CUSTOM = auto()
    WEB_SEARCH = auto()


class TextDeltaEvent(BaseModel):
    type: Literal[StreamEventType.TEXT_DELTA] = StreamEventType.TEXT_DELTA
    content: str


class TextDoneEvent(BaseModel):
    type: Literal[StreamEventType.TEXT_DONE] = StreamEventType.TEXT_DONE
    content: str | None = None


class ThinkingDeltaEvent(BaseModel):
    type: Literal[StreamEventType.THINKING_DELTA] = StreamEventType.THINKING_DELTA
    content: str


class ThinkingDoneEvent(BaseModel):
    type: Literal[StreamEventType.THINKING_DONE] = StreamEventType.THINKING_DONE
    content: str


class CustomFunctionCall(BaseModel):
    type: Literal[FunctionType.CUSTOM] = FunctionType.CUSTOM

    call_id: str
    name: str
    arguments: str = ""


class WebSearchActionSearch(BaseModel):
    type: Literal[WebSearchActionType.SEARCH] = WebSearchActionType.SEARCH

    query: str
    sources: list[str] | None = None

    @property
    def as_str(self) -> str:
        return f"Search: {self.query}."


class WebSearchActionOpenPage(BaseModel):
    type: Literal[WebSearchActionType.OPEN_PAGE] = WebSearchActionType.OPEN_PAGE

    url: str

    @property
    def as_str(self) -> str:
        return f"Open page: {self.url}."


class WebSearchActionFind(BaseModel):
    type: Literal[WebSearchActionType.FIND] = WebSearchActionType.FIND

    pattern: str
    url: str

    @property
    def as_str(self) -> str:
        return f"Find: {self.pattern} in {self.url}."


type WebsearchAction = Annotated[
    WebSearchActionSearch | WebSearchActionOpenPage | WebSearchActionFind,
    Field(discriminator="type"),
]


class WebSearchFunctionCall(BaseModel):
    type: Literal[FunctionType.WEB_SEARCH] = FunctionType.WEB_SEARCH

    id: str
    action: WebsearchAction | None
    status: WebSearchStatus = WebSearchStatus.SEARCHING

    @property
    def as_str(self) -> str:
        if self.action is None:
            return f"Search: {self.status.icon}"
        return f"{self.action.as_str} {self.status.icon}"


type FunctionCall = Annotated[
    CustomFunctionCall | WebSearchFunctionCall,
    Field(discriminator="type"),
]


class FunctionCallStartEvent(BaseModel):
    type: Literal[StreamEventType.FUNCTION_CALL_START] = (
        StreamEventType.FUNCTION_CALL_START
    )

    id: str
    item: FunctionCall


class FunctionCallArgsDeltaEvent(BaseModel):
    type: Literal[StreamEventType.FUNCTION_CALL_ARGS_DELTA] = (
        StreamEventType.FUNCTION_CALL_ARGS_DELTA
    )

    id: str
    delta: str


class FunctionCallArgsDoneEvent(BaseModel):
    type: Literal[StreamEventType.FUNCTION_CALL_ARGS_DONE] = (
        StreamEventType.FUNCTION_CALL_ARGS_DONE
    )

    id: str
    item: FunctionCall


class FunctionCallOutput(BaseModel):
    call_id: str
    output: str


class MessageStartEvent(BaseModel):
    type: Literal[StreamEventType.MESSAGE_START] = StreamEventType.MESSAGE_START
    message_id: str


class MessageDoneEvent(BaseModel):
    type: Literal[StreamEventType.MESSAGE_DONE] = StreamEventType.MESSAGE_DONE
    message_id: str
    stop_reason: str
    tools: list[FunctionCall]


class ErrorEvent(BaseModel):
    type: Literal[StreamEventType.ERROR] = StreamEventType.ERROR
    code: str
    message: str


type StreamEvent = (
    TextDeltaEvent
    | TextDoneEvent
    | FunctionCallStartEvent
    | FunctionCallArgsDeltaEvent
    | FunctionCallArgsDoneEvent
    | ThinkingDeltaEvent
    | ThinkingDoneEvent
    | MessageStartEvent
    | MessageDoneEvent
    | ErrorEvent
)


class ContentBlock(BaseModel):
    type: str


class TextContentBlock(ContentBlock):
    type: Literal["text"] = "text"
    text: str


class ThinkingContentBlock(ContentBlock):
    type: Literal["thinking"] = "thinking"
    thinking: str


class CompletedResponse(BaseModel):
    message_id: str
    role: Literal[MessageRole.assistant] = MessageRole.assistant

    thinking: list[ThinkingContentBlock] = Field(default_factory=list)
    texts: list[TextContentBlock] = Field(default_factory=list)
    tools: list[CustomFunctionCall] = Field(default_factory=list)


class FunctionCallDefinition(BaseModel):
    type: Literal[FunctionType.CUSTOM] = FunctionType.CUSTOM

    name: str
    description: str
    input_schema: dict[str, Any]


class WebSearchToolDefinition(BaseModel):
    type: Literal[FunctionType.WEB_SEARCH] = FunctionType.WEB_SEARCH

    search_context_size: Literal["low", "medium", "high"] = "high"


type ToolDefinition = FunctionCallDefinition | WebSearchToolDefinition

type ChatRequestMessageItem = (
    UserMessage | AssistantMessage | CustomFunctionCall | FunctionCallOutput
)


class ChatRequest(BaseModel):
    model: str
    messages: list[ChatRequestMessageItem]
    temperature: float | None = None
    tools: list[ToolDefinition] | None = None
    tool_choice: Literal["auto", "required"] | None = None
    instructions: str | None = None
