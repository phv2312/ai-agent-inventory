from typing import Final

from jinja2 import Template
from pydantic import BaseModel, Field

from agents.models.openai_responses import OpenAIResponsesModel
from agent.core.models.messages import MessageContent, TextContent, UserMessage
from agent.core.prompts.core import PromptsFactory
from agent.core.programs.base import BaseProgram


class NameSuggestion(BaseModel):
    name: str = Field(description="Suggested conversation name")


class NameSuggestionProgram(BaseProgram[NameSuggestion]):
    ModelOutCls = NameSuggestion
    DEFAULT_MAX_WORDS: Final[int] = 10
    DEFAULT_NAME: Final[str] = "Conversation"

    def __init__(
        self,
        model: OpenAIResponsesModel,
        model_name: str,
        *,
        max_words: int = DEFAULT_MAX_WORDS,
        default_name: str = DEFAULT_NAME,
        template: Template | None = None,
    ) -> None:
        super().__init__(model, model_name)
        self.max_words = max_words
        self.default_name = default_name
        self.template = template or PromptsFactory.PROGRAMS.get(
            "name_suggestion",
        )

    @staticmethod
    def _extract_text(content: str | list[MessageContent]) -> str:
        if isinstance(content, str):
            return content
        return "\n".join(
            block.text for block in content if isinstance(block, TextContent)
        )

    async def aprocess(self, message: UserMessage) -> NameSuggestion:
        user_text = self._extract_text(message.content).strip()
        if not user_text:
            return NameSuggestion(name=self.default_name)

        prompt = UserMessage(
            content=self.template.render(
                max_words=self.max_words,
                user_message=user_text,
            ),
        )
        return await super().aprocess(prompt)
