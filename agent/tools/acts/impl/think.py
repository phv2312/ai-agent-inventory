from typing import Literal

from rich.console import Console
from rich.panel import Panel

from agent.models.streams import FunctionCallOutput
from agent.tools.acts.models import BaseToolCall, IToolAct, ToolActResult
from agent.tools.schemas.registry import ThinkParameters, ToolNames

console = Console()


class ThinkToolCall(BaseToolCall[ThinkParameters]):
    name: Literal[ToolNames.THINK_TOOL] = ToolNames.THINK_TOOL


class ThinkAct(IToolAct[ThinkToolCall]):
    async def act(self, tool_call: ThinkToolCall) -> ToolActResult:
        yield f"{tool_call.params.reflection}\n\n"
        yield FunctionCallOutput(
            call_id=tool_call.id,
            output=tool_call.params.reflection,
        )
        console.print(
            Panel(
                f"Thought: {tool_call.params.reflection}",
                title="💭 Thought",
                style="bold magenta",
            ),
        )
