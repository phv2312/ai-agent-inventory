from collections.abc import Sequence
from dataclasses import dataclass
from functools import cached_property

from agents import Agent, RunResultStreaming, Runner
from agents.models.openai_responses import OpenAIResponsesModel
from jinja2 import Template

from agent.models.document import DocumentMetadata
from agent.models.messages import AssistantMessage, UserMessage
from agent.prompts.core import PromptsFactory
from agent.rag.chats.deps import ChatDeps
from agent.skills.lavish import load_instructions
from agent.storages.config import AnchorFields

from .tools import build_tools


@dataclass
class AgenticSettings:
    max_turns: int = 20
    top_k: int = 10
    model_name: str = ""


class AgenticChatStrategy:
    """OpenAI Agents SDK implementation of the application RAG agent."""

    def __init__(
        self,
        deps: ChatDeps,
        model: OpenAIResponsesModel,
        settings: AgenticSettings | None = None,
        template: Template | None = None,
    ) -> None:
        self.deps = deps
        self.model = model
        self.settings = settings or AgenticSettings()
        self.template = template or PromptsFactory.AGENTIC.get("agent2")

    @cached_property
    def visualization_guidance(self) -> str:
        return PromptsFactory.TOOLS.get("visualize_readme").render(
            vis_templates="",
        )

    async def get_doc_names(self, file_ids: list[str]) -> list[str]:
        """Resolve document names for scoped retrieval instructions."""
        if not file_ids:
            return []
        chunks = await self.deps.vectordb.retrieve_by_filter(
            {AnchorFields.FILE_ID: file_ids},
        )
        names: set[str] = set()
        for scored_chunk in chunks.root:
            if isinstance(scored_chunk.chunk.metadata, DocumentMetadata):
                names.add(scored_chunk.chunk.metadata.filename)
        return sorted(names)

    async def stream_async_answer(
        self,
        query: str,
        file_ids: list[str],
        *,
        history: Sequence[UserMessage | AssistantMessage] | None = None,
        memory_md_content: str = "",
        top_k: int | None = None,
        web_search_enabled: bool = False,
    ) -> RunResultStreaming:
        """Start one SDK-managed, streamed agent run."""
        doc_names = await self.get_doc_names(file_ids)
        instructions = self.template.render(
            doc_names=";".join(doc_names),
            memory_md_content=memory_md_content,
        )
        instructions = f"{instructions}\n\n{load_instructions()}"
        messages = [*(history or []), UserMessage(content=query)]
        agent = Agent(
            name="agentic-rag",
            model=self.model,
            instructions=instructions,
            tools=build_tools(
                vectordb=self.deps.vectordb,
                embedding_model=self.deps.embedding_model,
                file_ids=file_ids,
                top_k=top_k or self.settings.top_k,
                visualization_guidance=self.visualization_guidance,
                web_search_enabled=web_search_enabled,
            ),
        )
        return Runner.run_streamed(
            agent,
            input=[
                {
                    "role": message.role.value,
                    "content": str(message.content),
                }
                for message in messages
            ],
            max_turns=self.settings.max_turns,
        )
