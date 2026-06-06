from collections.abc import AsyncGenerator
from typing import Any, Protocol

from pydantic import BaseModel

from agent.models.streams import FunctionCallOutput

type ToolActResult = AsyncGenerator[str | FunctionCallOutput, None]


class BaseToolCall[ParamsT: BaseModel](BaseModel):
    name: str
    id: str
    params: ParamsT


class IToolAct[ToolCallT: BaseToolCall[Any]](Protocol):
    def act(self, tool_call: ToolCallT) -> ToolActResult:
        raise NotImplementedError
