from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from agent.models.streams import (
        ChatRequest,
        CompletedResponse,
        StreamEvent,
    )


class IChatModel(ABC):
    @abstractmethod
    def stream(
        self,
        request: "ChatRequest",
    ) -> AsyncGenerator["StreamEvent", None]:
        raise NotImplementedError

    @abstractmethod
    async def chat(
        self,
        request: "ChatRequest",
    ) -> "CompletedResponse":
        raise NotImplementedError

    @abstractmethod
    async def parse[ResponseFormatT: BaseModel](
        self,
        request: "ChatRequest",
        response_format: type[ResponseFormatT],
    ) -> ResponseFormatT:
        raise NotImplementedError
