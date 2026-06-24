import json
from collections.abc import AsyncGenerator
from typing import Literal, NotRequired, TypedDict, cast
from uuid import uuid4

import structlog
from anthropic import AsyncAnthropic, AsyncStream
from anthropic.lib.foundry import AsyncAnthropicFoundry
from anthropic.types import (
    MessageParam,
    ParsedMessage,
    RawMessageStreamEvent,
    ToolParam,
    ToolResultBlockParam,
    ToolUnionParam,
    ToolUseBlockParam,
    WebSearchTool20250305Param,
)
from pydantic import BaseModel

from agent.chats.exc import InvalidChatResponseError
from agent.chats.interface import IChatModel
from agent.models.messages import AssistantMessage, UserMessage
from agent.models.streams import (
    ChatRequest,
    CompletedResponse,
    CustomFunctionCall,
    ErrorEvent,
    FunctionCallArgsDoneEvent,
    FunctionCallStartEvent,
    FunctionCallOutput,
    FunctionType,
    MessageDoneEvent,
    MessageStartEvent,
    StreamEvent,
    TextContentBlock,
    TextDoneEvent,
    ThinkingContentBlock,
    ThinkingDoneEvent,
    WebSearchFunctionCall,
)

from .event_handler import AnthropicEventHandler

logger = structlog.get_logger(__name__)

_DEFAULT_MAX_TOKENS = 8192


class AnthropicToolChoiceAuto(TypedDict):
    type: Literal["auto"]


class AnthropicStreamParams(TypedDict):
    model: str
    max_tokens: int
    messages: list[MessageParam]
    temperature: NotRequired[float]
    system: NotRequired[str]
    tool_choice: NotRequired[AnthropicToolChoiceAuto]
    tools: NotRequired[list[ToolUnionParam]]


class AnthropicProvider(IChatModel):
    def __init__(
        self,
        client: AsyncAnthropic | AsyncAnthropicFoundry,
    ) -> None:
        self.client = client

    @staticmethod
    def parse_input_messages(request: ChatRequest) -> list[MessageParam]:
        result: list[MessageParam] = []

        for message in request.messages:
            if isinstance(message, CustomFunctionCall):
                param = MessageParam(
                    content=[
                        ToolUseBlockParam(
                            id=message.call_id,
                            input=json.loads(message.arguments),
                            name=message.name,
                            type="tool_use",
                        ),
                    ],
                    role="assistant",
                )
            elif isinstance(message, FunctionCallOutput):
                param = MessageParam(
                    content=[
                        ToolResultBlockParam(
                            tool_use_id=message.call_id,
                            content=message.output,
                            type="tool_result",
                        ),
                    ],
                    role="user",
                )
            elif isinstance(message, UserMessage | AssistantMessage):
                role: Literal["user", "assistant"] = "user"
                if isinstance(message, AssistantMessage):
                    role = "assistant"

                param = MessageParam(
                    content=str(message.content),
                    role=role,
                )
            else:
                raise TypeError(f"Unsupported message: {type(message)}")

            result.append(param)

        return result

    @staticmethod
    def parse_params(request: ChatRequest) -> AnthropicStreamParams:
        inp_messages = AnthropicProvider.parse_input_messages(request)
        params: AnthropicStreamParams = {
            "model": request.model,
            "max_tokens": _DEFAULT_MAX_TOKENS,
            "messages": inp_messages,
        }
        if request.temperature is not None:
            params["temperature"] = request.temperature
        if request.instructions:
            params["system"] = request.instructions
        if request.tool_choice == "auto":
            params["tool_choice"] = {"type": "auto"}

        tools: list[ToolUnionParam] = []
        for tool in request.tools or []:
            if tool.type == FunctionType.CUSTOM:
                tools.append(
                    ToolParam(
                        name=tool.name,
                        description=tool.description,
                        input_schema=tool.input_schema,
                    ),
                )
            elif tool.type == FunctionType.WEB_SEARCH:
                tools.append(
                    WebSearchTool20250305Param(
                        name="web_search",
                        type="web_search_20250305",
                    ),
                )
            else:
                raise ValueError(f"Unsupported tool type: {tool.type}")

        if tools:
            params["tools"] = tools

        return params

    async def parse_stream(
        self,
        stream_iter: AsyncStream[RawMessageStreamEvent],
    ) -> AsyncGenerator[StreamEvent, None]:
        parser = AnthropicEventHandler(stream=stream_iter)
        async for chunk in parser:
            yield chunk

    async def stream(
        self,
        request: ChatRequest,
    ) -> AsyncGenerator[StreamEvent, None]:
        async with self.client.messages.stream(
            **self.parse_params(request),
        ) as stream:
            typed_stream = cast(
                AsyncStream[RawMessageStreamEvent],
                stream,
            )
            async for event in self.parse_stream(typed_stream):
                yield event

    async def chat(
        self,
        request: ChatRequest,
    ) -> CompletedResponse:
        message_id: str | None = None
        thinking: list[ThinkingContentBlock] = []
        texts: list[TextContentBlock] = []
        pending_function_call: dict[str, CustomFunctionCall] = {}

        async for event in self.stream(request):
            match event:
                case MessageStartEvent():
                    message_id = event.message_id
                case ThinkingDoneEvent():
                    thinking.append(
                        ThinkingContentBlock(thinking=event.content),
                    )
                case TextDoneEvent():
                    if event.content is None:
                        logger.warning("Text content is None")
                        continue
                    texts.append(
                        TextContentBlock(text=event.content),
                    )
                case FunctionCallStartEvent():
                    if isinstance(event.item, CustomFunctionCall):
                        pending_function_call[event.id] = event.item
                case FunctionCallArgsDoneEvent():
                    if isinstance(event.item, WebSearchFunctionCall):
                        logger.info(
                            "Web search done",
                            call_id=event.id,
                            status=event.item.status,
                        )
                        continue
                    if event.id not in pending_function_call:
                        raise KeyError("Can not find function call")
                    pending_function_call[event.id] = event.item
                case MessageDoneEvent():
                    break
                case ErrorEvent():
                    raise ValueError(
                        f"Error: {event.code} {event.message}",
                    )

        return CompletedResponse(
            message_id=message_id or str(uuid4()),
            thinking=thinking,
            texts=texts,
            tools=list(pending_function_call.values()),
        )

    async def parse[ResponseFormatT: BaseModel](
        self,
        request: ChatRequest,
        response_format: type[ResponseFormatT],
    ) -> ResponseFormatT:
        params = dict(self.parse_params(request))
        params.pop("tools", None)
        params.pop("tool_choice", None)

        response: ParsedMessage[ResponseFormatT] = await self.client.messages.parse(
            **params,
            output_format=response_format,
        )

        parsed = response.parsed_output
        if parsed is None:
            raise InvalidChatResponseError(
                f"Anthropic refused to parse response: {response}",
            )
        return parsed
