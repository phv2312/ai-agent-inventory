from typing import Final

from agents import Agent, Runner
from agents.models.openai_responses import OpenAIResponsesModel
from pydantic import BaseModel

from agent.core.models.messages import UserMessage


class BaseProgram[ModelOutT: BaseModel]:
    ModelOutCls: type[ModelOutT]
    DEFAULT_TEMPERATURE: Final[float] = 0.0

    def __init__(self, model: OpenAIResponsesModel, model_name: str) -> None:
        self.model = model
        self.model_name = model_name

    async def aprocess(
        self,
        message: UserMessage,
    ) -> ModelOutT:
        agent = Agent(
            name=self.__class__.__name__,
            model=self.model,
            output_type=self.ModelOutCls,
        )
        result = await Runner.run(
            agent,
            input=str(message.content),
        )
        return result.final_output_as(self.ModelOutCls)
