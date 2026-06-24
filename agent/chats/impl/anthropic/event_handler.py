import json
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Iterator
from dataclasses import dataclass, field
from typing import Any

import structlog
from anthropic import AsyncStream
from anthropic.lib.streaming import (
    ParsedContentBlockStopEvent,
    ParsedMessageStopEvent,
)
from anthropic.types import (
    CitationsDelta,
    ContentBlockDeltaEvent,
    InputJSONDelta,
    RawContentBlockStartEvent,
    RawMessageStartEvent,
    RawMessageStreamEvent,
    ServerToolUseBlock,
    SignatureDelta,
    TextBlock,
    TextDelta,
    ThinkingBlock,
    ThinkingDelta,
    ToolUseBlock,
)
from pydantic import BaseModel

from agent.models.streams import (
    CustomFunctionCall,
    FunctionCallArgsDeltaEvent,
    FunctionCallArgsDoneEvent,
    FunctionCallStartEvent,
    MessageDoneEvent,
    MessageStartEvent,
    StreamEvent,
    TextDeltaEvent,
    TextDoneEvent,
    ThinkingDeltaEvent,
    ThinkingDoneEvent,
    WebSearchActionSearch,
    WebSearchFunctionCall,
    WebSearchStatus,
)

logger = structlog.get_logger(__name__)


@dataclass
class ParseScratch:
    message_id: str | None = None
    current_tool_id: str | None = None
    mp_id_function_call: dict[str, CustomFunctionCall] = field(
        default_factory=dict,
    )


class BaseAnthropicEventHandler[ModelT: BaseModel](ABC):
    Model: type[ModelT]

    def handle(
        self,
        event: ModelT,
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


class RawMessageStartEventHandler(
    BaseAnthropicEventHandler[RawMessageStartEvent],
):
    Model = RawMessageStartEvent

    def handle_event(
        self,
        event: RawMessageStartEvent,
        scratch: ParseScratch,
    ) -> Iterator[StreamEvent]:
        scratch.message_id = event.message.id
        if scratch.message_id is None:
            raise ValueError("message_id is None")

        yield MessageStartEvent(message_id=scratch.message_id)


class ContentBlockDeltaEventHandler(
    BaseAnthropicEventHandler[ContentBlockDeltaEvent],
):
    Model = ContentBlockDeltaEvent

    def handle_event(
        self,
        event: ContentBlockDeltaEvent,
        scratch: ParseScratch,
    ) -> Iterator[StreamEvent]:
        delta = event.delta
        if isinstance(delta, TextDelta):
            yield TextDeltaEvent(content=delta.text)
            return
        if isinstance(delta, ThinkingDelta):
            yield ThinkingDeltaEvent(content=delta.thinking)
            return
        if isinstance(delta, InputJSONDelta):
            if scratch.current_tool_id is None:
                logger.debug(
                    "input_json_delta without active tool_use block; skipping",
                )
                return
            yield FunctionCallArgsDeltaEvent(
                id=scratch.current_tool_id,
                delta=delta.partial_json,
            )
            return
        if isinstance(delta, CitationsDelta | SignatureDelta):
            logger.debug("Unhandled delta type", delta=delta.model_dump_json())
            return


class RawContentBlockStartEventHandler(
    BaseAnthropicEventHandler[RawContentBlockStartEvent],
):
    Model = RawContentBlockStartEvent

    def handle_event(
        self,
        event: RawContentBlockStartEvent,
        scratch: ParseScratch,
    ) -> Iterator[StreamEvent]:
        block = event.content_block
        if isinstance(block, ToolUseBlock):
            scratch.current_tool_id = block.id
            scratch.mp_id_function_call[block.id] = CustomFunctionCall(
                call_id=block.id,
                name=block.name,
            )
            yield FunctionCallStartEvent(
                id=block.id,
                item=scratch.mp_id_function_call[block.id],
            )
            return
        if isinstance(block, ServerToolUseBlock):
            if block.name != "web_search":
                return
            yield FunctionCallStartEvent(
                id=block.id,
                item=WebSearchFunctionCall(
                    id=block.id,
                    action=WebSearchActionSearch(
                        query="",
                        sources=None,
                    ),
                    status=WebSearchStatus.SEARCHING,
                ),
            )


class ParsedContentBlockStopEventHandler(
    BaseAnthropicEventHandler[Any],
):
    Model: type[Any] = ParsedContentBlockStopEvent

    def handle_event(
        self,
        event: ParsedContentBlockStopEvent,
        scratch: ParseScratch,
    ) -> Iterator[StreamEvent]:
        block = event.content_block
        if isinstance(block, TextBlock):
            if block.text:
                yield TextDeltaEvent(content="\n\n")
                yield TextDoneEvent(content=block.text)
        elif isinstance(block, ThinkingBlock):
            yield ThinkingDoneEvent(content=block.thinking)
            return
        elif isinstance(block, ToolUseBlock):
            if block.id not in scratch.mp_id_function_call:
                raise KeyError(f"Can not find function call, id={block.id}")

            tool_call = scratch.mp_id_function_call[block.id]
            tool_call.arguments = json.dumps(
                block.input,
            )
            yield FunctionCallArgsDoneEvent(
                id=block.id,
                item=tool_call,
            )
            scratch.current_tool_id = None
            return
        elif isinstance(block, ServerToolUseBlock):
            if block.name != "web_search":
                return
            yield FunctionCallArgsDoneEvent(
                id=block.id,
                item=WebSearchFunctionCall(
                    id=block.id,
                    action=WebSearchActionSearch(
                        query=str(block.input.get("query", "_")),
                        sources=None,
                    ),
                    status=WebSearchStatus.COMPLETED,
                ),
            )
            return


class ParsedMessageStopEventHandler(
    BaseAnthropicEventHandler[Any],
):
    Model: type[Any] = ParsedMessageStopEvent

    def handle_event(
        self,
        event: ParsedMessageStopEvent,
        scratch: ParseScratch,
    ) -> Iterator[StreamEvent]:
        stop_reason = str(event.message.stop_reason or "")
        yield MessageDoneEvent(
            message_id=scratch.message_id or event.message.id,
            stop_reason=stop_reason,
            tools=list(scratch.mp_id_function_call.values()),
        )


@dataclass
class AnthropicEventHandler:
    stream: AsyncStream[RawMessageStreamEvent]

    def __post_init__(self) -> None:
        self.event_handlers: dict[
            type[RawMessageStreamEvent],
            BaseAnthropicEventHandler[Any],
        ] = {
            RawMessageStartEvent: RawMessageStartEventHandler(),
            ContentBlockDeltaEvent: ContentBlockDeltaEventHandler(),
            RawContentBlockStartEvent: RawContentBlockStartEventHandler(),
            ParsedContentBlockStopEvent: ParsedContentBlockStopEventHandler(),
            ParsedMessageStopEvent: ParsedMessageStopEventHandler(),
        }

    async def __aiter__(
        self,
    ) -> AsyncGenerator[StreamEvent, None]:
        scratch = ParseScratch()
        async for event in self.stream:
            handler = self.event_handlers.get(type(event))
            if handler is None:
                continue
            for chunk in handler.handle(event, scratch):
                yield chunk
