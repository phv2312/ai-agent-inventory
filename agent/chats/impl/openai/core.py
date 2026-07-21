from collections.abc import AsyncGenerator
from typing import Any, Literal, NotRequired, TypedDict
from uuid import uuid4

import structlog
from openai import AsyncOpenAI, AsyncStream
from openai.types.responses import (
    FunctionToolParam,
    ParsedResponse,
    Response,
    ResponseStreamEvent,
    ToolParam,
    WebSearchToolParam,
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
    FunctionCallOutput,
    FunctionType,
    MessageDoneEvent,
    StreamEvent,
    TextContentBlock,
    TextDoneEvent,
    ThinkingContentBlock,
    ThinkingDoneEvent,
    WebSearchFunctionCall,
)

from .event_handler import OpenAIEventHandler

logger = structlog.get_logger(__name__)


class OpenAIStreamParams(TypedDict):
    input: list[dict[str, Any]]
    model: str
    temperature: NotRequired[float]
    instructions: NotRequired[str]
    tool_choice: NotRequired[Literal["auto", "required"]]
    tools: NotRequired[list[ToolParam]]


class OpenAIProvider(IChatModel):
    def __init__(
        self,
        client: AsyncOpenAI,
    ) -> None:
        self.client = client

    @staticmethod
    def _responses_input_messages(
        request: ChatRequest,
    ) -> list[dict[str, Any]]:
        input_messages: list[dict[str, Any]] = []

        for message in request.messages:
            if isinstance(message, UserMessage | AssistantMessage):
                content = message.content
                if not isinstance(content, str):
                    content = str(content)
                input_messages.append(
                    {
                        "role": message.role,
                        "content": content,
                    },
                )
            elif isinstance(message, CustomFunctionCall):
                input_messages.append(
                    {
                        **message.model_dump(),
                        "type": "function_call",
                    },
                )
            elif isinstance(message, FunctionCallOutput):
                input_messages.append(
                    {
                        "call_id": message.call_id,
                        "output": [item.model_dump() for item in message.output],
                        "type": "function_call_output",
                    },
                )

        return input_messages

    @staticmethod
    def parse_params(request: ChatRequest) -> OpenAIStreamParams:
        params: OpenAIStreamParams = {
            "input": OpenAIProvider._responses_input_messages(request),
            "model": request.model,
        }

        if request.temperature:
            params["temperature"] = request.temperature

        if request.instructions:
            params["instructions"] = request.instructions

        if request.tool_choice:
            params["tool_choice"] = request.tool_choice

        openai_tools: list[ToolParam] = []
        for tool in request.tools or []:
            if tool.type == FunctionType.CUSTOM:
                openai_tools.append(
                    FunctionToolParam(
                        name=tool.name,
                        description=tool.description,
                        parameters=tool.input_schema,
                        strict=True,
                        type="function",
                    ),
                )
            elif tool.type == FunctionType.WEB_SEARCH:
                openai_tools.append(
                    WebSearchToolParam(
                        search_context_size=tool.search_context_size,
                        type="web_search",
                    ),
                )

        if openai_tools:
            params["tools"] = openai_tools

        return params

    async def stream(
        self,
        request: ChatRequest,
    ) -> AsyncGenerator[StreamEvent, None]:
        async for stream_event in self.parse_stream(
            await self.client.responses.create(
                **self.parse_params(request),  # type: ignore[arg-type]
                stream=True,
                parallel_tool_calls=False,
            ),
        ):
            yield stream_event

    async def parse_stream(
        self,
        stream_iter: Response | AsyncStream[ResponseStreamEvent],
    ) -> AsyncGenerator[StreamEvent, None]:
        parser = OpenAIEventHandler(stream=stream_iter)
        async for chunk in parser:
            yield chunk

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
                case FunctionCallArgsDoneEvent():
                    if isinstance(event.item, WebSearchFunctionCall):
                        logger.info(
                            "Web search done",
                            call_id=event.id,
                            status=event.item.status,
                        )
                        continue
                    pending_function_call[event.id] = event.item
                case MessageDoneEvent():
                    message_id = event.message_id
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
        params = self.parse_params(request)
        params.pop("tools", None)
        params.pop("tool_choice", None)

        response: ParsedResponse[ResponseFormatT] = await self.client.responses.parse(
            **params,  # type: ignore[arg-type]
            text_format=response_format,
        )

        parsed = response.output_parsed
        if parsed is None:
            raise InvalidChatResponseError(
                f"OpenAI refused to parse response: {response}",
            )
        return parsed
