import json
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field

import structlog
from rich.console import Console
from rich.panel import Panel

from agent.chats.interface import IChatModel
from agent.models.messages import AssistantMessage
from agent.models.streams import (
    ChatRequest,
    CustomFunctionCall,
    ErrorEvent,
    FunctionCallOutput,
    FunctionCallStartEvent,
    FunctionCallProgressEvent,
    MessageDoneEvent,
    StreamEvent,
    TextDeltaEvent,
    WebSearchFunctionCall,
)
from agent.tools.acts.registry import ToolActsRegistry, ToolParser
from agent.tracer import llm_span, tracer_provider

logger = structlog.get_logger(__name__)
console = Console()
tracer = tracer_provider.get_tracer(__name__)


@dataclass
class AgentTurnState:
    assistant_text: str = ""
    mp_id_tool_name: dict[str, str] = field(default_factory=dict)
    function_calls: list[CustomFunctionCall] = field(default_factory=list)


@dataclass
class ReAct:
    streamer: IChatModel
    request: ChatRequest
    actor_registry: ToolActsRegistry
    max_turns: int = field(default=20)

    async def stream(self) -> AsyncGenerator[StreamEvent, None]:
        for turn_idx in range(self.max_turns):
            turn = AgentTurnState()

            # Handle text delta and pre-built tools
            async for chunk in self.handle_llm_stream(
                self.request,
                turn,
                turn_idx=turn_idx,
            ):
                yield chunk
            has_tool_calls = len(turn.function_calls) > 0

            if turn.assistant_text:
                self.request.messages.append(
                    AssistantMessage.from_content(turn.assistant_text),
                )
            self.request.messages.extend(turn.function_calls)

            if not has_tool_calls:
                break

            logger.info(
                "Handling tool calls",
                turn_idx=turn_idx,
                function_calls=len(turn.function_calls),
            )

            # Handle custom function call & its progress
            async for event in self.handle_tool_calls(
                function_calls=turn.function_calls,
            ):
                yield event

    async def handle_llm_stream(
        self,
        request: ChatRequest,
        state: AgentTurnState,
        *,
        turn_idx: int = 0,
    ) -> AsyncGenerator[StreamEvent, None]:
        with llm_span(
            tracer,
            f"ReAct.llm.turn_{turn_idx}",
            request,
        ) as span:
            async for event in self.streamer.stream(request):
                if isinstance(event, ErrorEvent):
                    msg = f"Stream error {event.code}: {event.message}"
                    raise TypeError(msg)
                if isinstance(event, TextDeltaEvent):
                    state.assistant_text += event.content
                elif isinstance(event, FunctionCallStartEvent):
                    if isinstance(event.item, CustomFunctionCall):
                        state.mp_id_tool_name[event.id] = event.item.name
                    elif isinstance(event.item, WebSearchFunctionCall):
                        yield FunctionCallProgressEvent(
                            id=event.id, delta=event.item.as_str
                        )
                elif isinstance(event, MessageDoneEvent):
                    state.function_calls = [
                        tool_call
                        for tool_call in event.tools
                        if isinstance(tool_call, CustomFunctionCall)
                    ]
                yield event
            span.set_output(
                {
                    "text": state.assistant_text,
                    "tool_calls": [call.name for call in state.function_calls],
                },
            )

    async def handle_tool_calls(
        self,
        function_calls: list[CustomFunctionCall],
    ) -> AsyncGenerator[StreamEvent, None]:
        for function_call in function_calls:
            console.print(
                Panel(
                    f"[Executing: {function_call.name}(#{function_call.call_id})",
                    title="🔧 Tool Call",
                    style="bold cyan",
                ),
            )

            actor = self.actor_registry.get(function_call.name)
            parsed_function_call = ToolParser.from_function_call(
                function_call,
            ).parsed
            if parsed_function_call is None or actor is None:
                logger.warning(
                    "Unhandled tool call; emitting error output",
                    function_call=function_call,
                    actor=actor,
                    parsed_function_call=parsed_function_call,
                )
                self.request.messages.append(
                    FunctionCallOutput(
                        call_id=function_call.call_id,
                        output=json.dumps(
                            {
                                "status": "error",
                                "message": (
                                    f"Tool '{function_call.name}' is not "
                                    "available or could not be parsed."
                                ),
                            },
                            ensure_ascii=False,
                        ),
                    ),
                )
                continue

            async for output_event in actor.act(parsed_function_call):
                if isinstance(output_event, str):
                    yield FunctionCallProgressEvent(
                        id=function_call.call_id,
                        delta=output_event,
                    )
                elif isinstance(output_event, FunctionCallOutput):
                    self.request.messages.append(output_event)
                else:
                    logger.warning(
                        "Unknown output event",
                        output_event=output_event,
                    )
