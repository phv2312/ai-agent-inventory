import json
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any

import structlog
from rich.console import Console
from rich.panel import Panel

from agent.chats.interface import IChatModel
from agent.models.messages import AssistantMessage, UserMessage
from agent.models.streams import (
    ChatRequest,
    CustomFunctionCall,
    ErrorEvent,
    FunctionCallArgsDeltaEvent,
    FunctionCallArgsDoneEvent,
    FunctionCallDefinition,
    FunctionCallOutput,
    FunctionCallStartEvent,
    FunctionCallTextDeltaEvent,
    MessageDoneEvent,
    MessageStartEvent,
    StreamEvent,
    TextDeltaEvent,
    TextDoneEvent,
    ThinkingDeltaEvent,
    ThinkingDoneEvent,
    ToolDefinition,
)
from agent.orchestrators.agent_tool import AgentAsToolAct, AgentToolCall
from agent.orchestrators.context import AgentContext, AgentTurnState
from agent.tools.acts.models import BaseToolCall, IToolAct
from agent.tools.acts.registry import ToolParser
from agent.tools.resolver import ToolResolver
from agent.tracer import llm_span, tracer_provider

logger = structlog.get_logger(__name__)
console = Console()
tracer = tracer_provider.get_tracer(__name__)

_STREAM_EVENT_TYPES = (
    TextDeltaEvent,
    TextDoneEvent,
    ThinkingDeltaEvent,
    ThinkingDoneEvent,
    FunctionCallStartEvent,
    FunctionCallTextDeltaEvent,
    FunctionCallArgsDeltaEvent,
    FunctionCallArgsDoneEvent,
    MessageStartEvent,
    MessageDoneEvent,
    ErrorEvent,
)


type ResolvedTool = IToolAct[Any] | AgentAsToolAct
type ParsedToolCall = AgentToolCall | BaseToolCall[Any]


@dataclass
class ReActAgent:
    streamer: IChatModel
    resolver: ToolResolver
    model: str = ""
    instructions: str | None = None
    tools: list[ToolDefinition] | None = None
    temperature: float | None = None
    max_turns: int = field(default=20)

    @property
    def tool_names(self) -> frozenset[str]:
        if not self.tools:
            return frozenset()
        return frozenset(
            tool.name for tool in self.tools if isinstance(tool, FunctionCallDefinition)
        )

    def build_request(self, query: str) -> ChatRequest:
        if not self.model:
            raise ValueError("model is required to build agent request")
        return ChatRequest(
            model=self.model,
            messages=[UserMessage(content=query)],
            tools=self.tools,
            temperature=self.temperature,
            instructions=self.instructions,
        )

    async def stream(
        self,
        request: ChatRequest,
    ) -> AsyncGenerator[StreamEvent, None]:
        context = AgentContext(request=request.model_copy(deep=True))
        for turn_idx in range(self.max_turns):
            turn = context.new_turn()
            async for chunk in self.handle_llm_stream(
                context,
                turn,
                turn_idx=turn_idx,
            ):
                yield chunk
            has_tool_calls = len(turn.function_calls) > 0

            if turn.assistant_text:
                context.request.messages.append(
                    AssistantMessage.from_content(turn.assistant_text),
                )
            context.request.messages.extend(turn.function_calls)

            if not has_tool_calls:
                break

            logger.info(
                "Handling tool calls",
                turn_idx=turn_idx,
                function_calls=len(turn.function_calls),
            )

            async for event in self.handle_tool_calls(
                context=context,
                function_calls=turn.function_calls,
            ):
                yield event

    async def handle_llm_stream(
        self,
        context: AgentContext,
        state: AgentTurnState,
        *,
        turn_idx: int = 0,
    ) -> AsyncGenerator[StreamEvent, None]:
        with llm_span(
            tracer,
            f"ReActAgent.llm.turn_{turn_idx}",
            context.request,
        ) as span:
            async for event in self.streamer.stream(context.request):
                if isinstance(event, ErrorEvent):
                    msg = f"Stream error {event.code}: {event.message}"
                    raise TypeError(msg)
                if isinstance(event, TextDeltaEvent):
                    state.assistant_text += event.content
                elif isinstance(event, FunctionCallStartEvent) and isinstance(
                    event.item,
                    CustomFunctionCall,
                ):
                    state.mp_id_tool_name[event.id] = event.item.name
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
        *,
        context: AgentContext,
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

            if function_call.name not in self.tool_names:
                context.request.messages.append(
                    self.error_output(
                        function_call.call_id,
                        f"Tool '{function_call.name}' is not allowed for this agent.",
                    ),
                )
                continue

            try:
                resolved: ResolvedTool | None = self.resolver.get(
                    function_call.name,
                )
            except ValueError as exc:
                context.request.messages.append(
                    self.error_output(function_call.call_id, str(exc)),
                )
                continue

            actor, parsed = self.resolve_actor_call(
                function_call,
                resolved,
            )
            if parsed is None or actor is None:
                logger.warning(
                    "Unhandled tool call; emitting error output",
                    function_call=function_call,
                    actor=actor,
                    parsed_function_call=parsed,
                )
                context.request.messages.append(
                    self.error_output(
                        function_call.call_id,
                        (
                            f"Tool '{function_call.name}' is not "
                            "available or could not be parsed."
                        ),
                    ),
                )
                continue

            async for output_event in actor.act(parsed):
                if isinstance(output_event, _STREAM_EVENT_TYPES):
                    yield output_event
                elif isinstance(output_event, str):
                    yield FunctionCallTextDeltaEvent(
                        id=function_call.call_id,
                        delta=output_event,
                    )
                elif isinstance(output_event, FunctionCallOutput):
                    context.request.messages.append(output_event)
                else:
                    logger.warning(
                        "Unknown output event",
                        output_event=output_event,
                    )

    def resolve_actor_call(
        self,
        function_call: CustomFunctionCall,
        resolved: ResolvedTool | None,
    ) -> tuple[ResolvedTool | None, ParsedToolCall | None]:
        if resolved is None:
            return None, None
        if isinstance(resolved, AgentAsToolAct):
            return resolved, AgentAsToolAct.from_function_call(
                function_call.name,
                function_call.call_id,
                function_call.arguments,
            )
        parsed = ToolParser.from_function_call(function_call).parsed
        return resolved, parsed

    @staticmethod
    def error_output(call_id: str, message: str) -> FunctionCallOutput:
        return FunctionCallOutput(
            call_id=call_id,
            output=json.dumps(
                {"status": "error", "message": message},
                ensure_ascii=False,
            ),
        )


ReAct = ReActAgent
