from collections.abc import Sequence
from typing import cast

from openai import AsyncAzureOpenAI
from pydantic import BaseModel

from agent.models.messages import AssistantMessage, Messages, SystemMessage, UserMessage
from .exc import ParsedResultError


class BaseProgram[ModelOutT: BaseModel]:
    ModelOutCls: type[BaseModel]

    def __init__(
        self,
        api_key: str,
        api_version: str,
        azure_endpoint: str,
        deployment_name: str,
    ) -> None:
        self.openai = AsyncAzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=azure_endpoint,
        )
        self.deployment_name = deployment_name

    async def aprocess(
        self,
        message: UserMessage | None = None,
        system_message: SystemMessage | None = None,
        history: Sequence[UserMessage | AssistantMessage] | None = None,
    ) -> ModelOutT:
        messages = Messages.from_conversation(
            message=message,
            system_message=system_message,
            history=history,
        ).as_openai_list()

        completion = await self.openai.beta.chat.completions.parse(
            model=self.deployment_name,
            messages=messages,
            response_format=self.ModelOutCls,
            temperature=0.0,
        )

        first_choice = completion.choices[0].message
        if first_choice.refusal:
            raise ParsedResultError(first_choice.refusal)
        return cast(ModelOutT, first_choice.parsed)
