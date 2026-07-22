from typing import Literal

from rich.console import Console
from rich.panel import Panel

from agent.models.streams import FunctionCallOutput, TextItemOutput
from agent.tools.acts.models import BaseToolCall, IToolAct, ToolActResult
from agent.tools.schemas.registry import ThinkParameters, ToolNames
from agent.tracer import tool_span, tracer_provider

console = Console()
tracer = tracer_provider.get_tracer(__name__)


class ThinkToolCall(BaseToolCall[ThinkParameters]):
    name: Literal[ToolNames.THINK_TOOL] = ToolNames.THINK_TOOL


class ThinkAct(IToolAct[ThinkToolCall]):
    async def act(self, tool_call: ThinkToolCall) -> ToolActResult:
        with tool_span(tracer, "ThinkAct.act", tool_call) as span:
            yield f"Think: {tool_call.params.reflection}\n\n"
            output = FunctionCallOutput(
                call_id=tool_call.id,
                output=[TextItemOutput(text=tool_call.params.reflection)],
            )
            span.set_output(output)
            yield output
            console.print(
                Panel(
                    f"Thought: {tool_call.params.reflection}",
                    title="💭 Thought",
                    style="bold magenta",
                ),
            )
