import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pydantic import Field

from agent.models.streams import (
    FunctionCallOutput,
    TextDeltaEvent,
)
from agent.tools.acts.models import BaseToolCall, ToolActResult
from agent.tools.schemas.registry import BaseToolParameters

if TYPE_CHECKING:
    from agent.orchestrators.react import ReActAgent


class AgentToolParams(BaseToolParameters):
    query: str = Field(..., description="Task delegated to the child agent")


class AgentToolCall(BaseToolCall[AgentToolParams]):
    name: str
    id: str
    params: AgentToolParams


@dataclass
class AgentAsToolAct:
    agent: "ReActAgent"
    agent_name: str

    @classmethod
    def from_function_call(
        cls,
        function_call_name: str,
        call_id: str,
        arguments: str,
    ) -> AgentToolCall | None:
        try:
            params = AgentToolParams.model_validate_json(arguments)
        except Exception:
            return None
        return AgentToolCall(
            name=function_call_name,
            id=call_id,
            params=params,
        )

    async def act(self, tool_call: BaseToolCall[Any]) -> ToolActResult:
        if not isinstance(tool_call, AgentToolCall):
            msg = "Tool call must be an AgentToolCall"
            raise TypeError(msg)

        child_request = self.agent.build_request(tool_call.params.query)
        text_parts: list[str] = []
        try:
            async for event in self.agent.stream(child_request):
                if isinstance(event, TextDeltaEvent):
                    text_parts.append(event.content)
                yield event
        except Exception as exc:
            yield FunctionCallOutput(
                call_id=tool_call.id,
                output=json.dumps(
                    {
                        "status": "error",
                        "message": str(exc),
                    },
                    ensure_ascii=False,
                ),
            )
            return

        yield FunctionCallOutput(
            call_id=tool_call.id,
            output="".join(text_parts),
        )
