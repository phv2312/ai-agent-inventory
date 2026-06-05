from typing import Protocol

from pydantic import BaseModel

from agent.models.messages import UserMessage


class IProgram[ModelOutT: BaseModel](Protocol):
    async def aprocess(
        self,
        message: UserMessage,
    ) -> ModelOutT: ...
