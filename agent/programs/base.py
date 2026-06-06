from typing import Final

from pydantic import BaseModel

from agent.chats.interface import IChatModel
from agent.models.messages import UserMessage
from agent.models.streams import ChatRequest


class BaseProgram[ModelOutT: BaseModel]:
    ModelOutCls: type[ModelOutT]
    DEFAULT_TEMPERATURE: Final[float] = 0.0

    def __init__(self, chat_model: IChatModel, model_name: str) -> None:
        self.chat_model = chat_model
        self.model_name = model_name

    async def aprocess(
        self,
        message: UserMessage,
    ) -> ModelOutT:
        request = ChatRequest(
            model=self.model_name,
            messages=[message],
            temperature=self.DEFAULT_TEMPERATURE,
        )
        return await self.chat_model.parse(
            request=request,
            response_format=self.ModelOutCls,
        )
