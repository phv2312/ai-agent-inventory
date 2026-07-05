from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Iterator
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from openai import AsyncStream
from openai.types.responses import (
    Response,
    ResponseCompletedEvent,
    ResponseCreatedEvent,
    ResponseErrorEvent,
    ResponseFunctionCallArgumentsDeltaEvent,
    ResponseFunctionCallArgumentsDoneEvent,
    ResponseFunctionWebSearch,
    ResponseOutputItemAddedEvent,
    ResponseOutputItemDoneEvent,
    ResponseReasoningTextDeltaEvent,
    ResponseReasoningTextDoneEvent,
    ResponseStreamEvent,
    ResponseTextDeltaEvent,
    ResponseTextDoneEvent,
)
from openai.types.responses.response_function_tool_call import (
    ResponseFunctionToolCall,
)
from openai.types.responses.response_function_web_search import (
    ActionFind,
    ActionOpenPage,
    ActionSearch,
)
from pydantic import BaseModel

from agent.models.streams import (
    CustomFunctionCall,
    ErrorEvent,
    FunctionCallArgsDeltaEvent,
    FunctionCallArgsDoneEvent,
    FunctionCallStartEvent,
    MessageDoneEvent,
    MessageStartEvent,
    ResponseUsage,
    StreamEvent,
    TextDeltaEvent,
    TextDoneEvent,
    ThinkingDeltaEvent,
    ThinkingDoneEvent,
    WebSearchActionFind,
    WebSearchActionOpenPage,
    WebSearchActionSearch,
    WebSearchFunctionCall,
    WebSearchStatus,
    WebsearchAction,
)


class Utils:
    @staticmethod
    def parse_web_search_action(
        item: ResponseFunctionWebSearch,
    ) -> WebsearchAction | None:
        action: WebsearchAction | None = None
        if isinstance(item.action, ActionSearch):
            action = WebSearchActionSearch(
                query=item.action.query or "_",
                sources=[source.url for source in item.action.sources or []],
            )
        elif isinstance(item.action, ActionOpenPage):
            action = WebSearchActionOpenPage(
                url=item.action.url or "",
            )
        elif isinstance(item.action, ActionFind):
            action = WebSearchActionFind(
                pattern=item.action.pattern or "",
                url=item.action.url or "",
            )
        return action


@dataclass
class ParseScratch:
    message_id: str | None = None
    mp_id_function_call: dict[str, CustomFunctionCall] = field(
        default_factory=dict,
    )


class BaseEventHandler[ModelT: BaseModel](ABC):
    Model: type[ModelT]

    def handle(
        self,
        event: ResponseStreamEvent,
        scratch: ParseScratch,
    ) -> Iterator[StreamEvent]:
        if not isinstance(event, self.Model):
            msg = f"Event must be an instance of {self.Model.__name__}"
            raise TypeError(msg)
        return self.handle_event(event, scratch)

    @abstractmethod
    def handle_event(
        self,
        event: ModelT,
        scratch: ParseScratch,
    ) -> Iterator[StreamEvent]:
        raise NotImplementedError


class CreatedEventHandler(BaseEventHandler[ResponseCreatedEvent]):
    Model = ResponseCreatedEvent

    def handle_event(
        self,
        event: ResponseCreatedEvent,
        scratch: ParseScratch,
    ) -> Iterator[StreamEvent]:
        scratch.message_id = event.response.id or str(uuid4())
        yield MessageStartEvent(message_id=scratch.message_id)


@dataclass
class OutputItemAddedEventHandler(
    BaseEventHandler[ResponseOutputItemAddedEvent],
):
    Model = ResponseOutputItemAddedEvent

    def handle_event(
        self,
        event: ResponseOutputItemAddedEvent,
        scratch: ParseScratch,
    ) -> Iterator[StreamEvent]:
        item = event.item
        if isinstance(item, ResponseFunctionToolCall):
            if item.id is None:
                raise ValueError("Item ID is required for function call")
            scratch.mp_id_function_call[item.id] = CustomFunctionCall(
                call_id=item.call_id,
                name=item.name,
            )
            yield FunctionCallStartEvent(
                id=item.id,
                item=scratch.mp_id_function_call[item.id],
            )
            return
        if isinstance(item, ResponseFunctionWebSearch):
            yield FunctionCallStartEvent(
                id=item.id,
                item=WebSearchFunctionCall(
                    id=item.id,
                    action=Utils.parse_web_search_action(item),
                    status=WebSearchStatus.SEARCHING,
                ),
            )


@dataclass
class OutputItemDoneEventHandler(
    BaseEventHandler[ResponseOutputItemDoneEvent],
):
    Model = ResponseOutputItemDoneEvent

    def handle_event(
        self,
        event: ResponseOutputItemDoneEvent,
        _scratch: ParseScratch,
    ) -> Iterator[StreamEvent]:
        mp_str_status: dict[str, WebSearchStatus] = {
            "completed": WebSearchStatus.COMPLETED,
            "failed": WebSearchStatus.FAILED,
        }
        item = event.item
        if not isinstance(item, ResponseFunctionWebSearch):
            return
        yield FunctionCallArgsDoneEvent(
            id=item.id,
            item=WebSearchFunctionCall(
                id=item.id,
                action=Utils.parse_web_search_action(item),
                status=mp_str_status.get(
                    item.status,
                    WebSearchStatus.SEARCHING,
                ),
            ),
        )


class TextDeltaEventHandler(BaseEventHandler[ResponseTextDeltaEvent]):
    Model = ResponseTextDeltaEvent

    def handle_event(
        self,
        event: ResponseTextDeltaEvent,
        _scratch: ParseScratch,
    ) -> Iterator[StreamEvent]:
        yield TextDeltaEvent(content=event.delta)


class TextDoneEventHandler(BaseEventHandler[ResponseTextDoneEvent]):
    Model = ResponseTextDoneEvent

    def handle_event(
        self,
        event: ResponseTextDoneEvent,
        _scratch: ParseScratch,
    ) -> Iterator[StreamEvent]:
        yield TextDoneEvent(content=event.text)


class ReasoningTextDeltaEventHandler(
    BaseEventHandler[ResponseReasoningTextDeltaEvent],
):
    Model = ResponseReasoningTextDeltaEvent

    def handle_event(
        self,
        event: ResponseReasoningTextDeltaEvent,
        _scratch: ParseScratch,
    ) -> Iterator[StreamEvent]:
        yield ThinkingDeltaEvent(content=event.delta)


class ReasoningTextDoneEventHandler(
    BaseEventHandler[ResponseReasoningTextDoneEvent],
):
    Model = ResponseReasoningTextDoneEvent

    def handle_event(
        self,
        event: ResponseReasoningTextDoneEvent,
        _scratch: ParseScratch,
    ) -> Iterator[StreamEvent]:
        yield ThinkingDoneEvent(content=event.text)


class FunctionCallArgumentsDeltaEventHandler(
    BaseEventHandler[ResponseFunctionCallArgumentsDeltaEvent],
):
    Model = ResponseFunctionCallArgumentsDeltaEvent

    def handle_event(
        self,
        event: ResponseFunctionCallArgumentsDeltaEvent,
        _scratch: ParseScratch,
    ) -> Iterator[StreamEvent]:
        yield FunctionCallArgsDeltaEvent(
            id=event.item_id,
            delta=event.delta,
        )


class FunctionCallArgumentsDoneEventHandler(
    BaseEventHandler[ResponseFunctionCallArgumentsDoneEvent],
):
    Model = ResponseFunctionCallArgumentsDoneEvent

    def handle_event(
        self,
        event: ResponseFunctionCallArgumentsDoneEvent,
        scratch: ParseScratch,
    ) -> Iterator[StreamEvent]:
        if event.item_id not in scratch.mp_id_function_call:
            raise KeyError("Can not find function call")
        scratch.mp_id_function_call[event.item_id].arguments = event.arguments
        yield FunctionCallArgsDoneEvent(
            id=event.item_id,
            item=scratch.mp_id_function_call[event.item_id],
        )


class CompletedEventHandler(BaseEventHandler[ResponseCompletedEvent]):
    Model = ResponseCompletedEvent

    def handle_event(
        self,
        event: ResponseCompletedEvent,
        scratch: ParseScratch,
    ) -> Iterator[StreamEvent]:
        response = event.response
        stop_reason = str(response.status or "")
        if response.incomplete_details:
            stop_reason = str(response.incomplete_details.reason or "")

        if scratch.message_id is None:
            raise ValueError("Message ID is required")

        usage = ResponseUsage()
        if response.usage:
            usage = ResponseUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                total_tokens=response.usage.total_tokens,
            )

        yield MessageDoneEvent(
            message_id=scratch.message_id,
            stop_reason=stop_reason,
            tools=list(scratch.mp_id_function_call.values()),
            usage=usage,
        )


class ErrorEventHandler(BaseEventHandler[ResponseErrorEvent]):
    Model = ResponseErrorEvent

    def handle_event(
        self,
        event: ResponseErrorEvent,
        _scratch: ParseScratch,
    ) -> Iterator[StreamEvent]:
        yield ErrorEvent(
            code=event.code or "",
            message=event.message,
        )


@dataclass
class OpenAIEventHandler:
    stream: Response | AsyncStream[ResponseStreamEvent]

    def __post_init__(self) -> None:
        self.event_handlers: dict[
            type[ResponseStreamEvent],
            BaseEventHandler[Any],
        ] = {
            ResponseCreatedEvent: CreatedEventHandler(),
            ResponseOutputItemAddedEvent: OutputItemAddedEventHandler(),
            ResponseOutputItemDoneEvent: OutputItemDoneEventHandler(),
            ResponseTextDeltaEvent: TextDeltaEventHandler(),
            ResponseTextDoneEvent: TextDoneEventHandler(),
            ResponseReasoningTextDeltaEvent: ReasoningTextDeltaEventHandler(),
            ResponseReasoningTextDoneEvent: ReasoningTextDoneEventHandler(),
            ResponseFunctionCallArgumentsDeltaEvent: (
                FunctionCallArgumentsDeltaEventHandler()
            ),
            ResponseFunctionCallArgumentsDoneEvent: (
                FunctionCallArgumentsDoneEventHandler()
            ),
            ResponseCompletedEvent: CompletedEventHandler(),
            ResponseErrorEvent: ErrorEventHandler(),
        }

    async def __aiter__(
        self,
    ) -> AsyncGenerator[StreamEvent, None]:
        if isinstance(self.stream, Response):
            raise TypeError(
                "Stream must be an instance of AsyncStream[ResponseStreamEvent]",
            )

        scratch = ParseScratch()

        async for event in self.stream:
            handler = self.event_handlers.get(type(event))
            if handler is None:
                continue
            for chunk in handler.handle(event, scratch):
                yield chunk
