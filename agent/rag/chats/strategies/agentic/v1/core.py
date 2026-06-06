from collections.abc import AsyncGenerator, Sequence
from dataclasses import dataclass
from functools import cached_property
from typing import Final

import structlog
from jinja2 import Template

from agent.models.document import DocumentMetadata, ScoredChunks
from agent.models.messages import AssistantMessage, UserMessage
from agent.models.streams import ChatRequest, StreamEvent, ToolDefinition
from agent.orchestrators import ReAct
from agent.prompts.core import PromptsFactory
from agent.rag.chats.deps import ChatDeps
from agent.storages.config import AnchorFields
from agent.tools.acts.registry import ToolActsRegistry
from agent.tools.schemas.registry import ToolSchemaRegistry

logger = structlog.get_logger()


@dataclass
class AgenticSettings:
    max_turns: int = 20
    top_k: int = 10
    temperature: float = 0.1
    model_name: str = ""


@dataclass
class Utils:
    deps: ChatDeps

    async def get_doc_names(
        self,
        file_ids: list[str],
    ) -> Sequence[str]:
        if not file_ids:
            return []

        scored_chunks = await self.deps.vectordb.retrieve_by_filter(
            {AnchorFields.FILE_ID: list(file_ids)},
        )
        doc_names: set[str] = set()
        for scored_chunk in scored_chunks.root:
            filename: str | None = None
            if isinstance(scored_chunk.chunk.metadata, DocumentMetadata):
                filename = scored_chunk.chunk.metadata.filename
            if filename:
                doc_names.add(str(filename))
        return list(doc_names)


class AgenticChatStrategy:
    DEFAULT_MAX_TURNS: Final[int] = 20
    DEFAULT_TEMPERATURE: Final[float] = 0.1
    DEFAULT_TOP_K: Final[int] = 10

    def __init__(
        self,
        deps: ChatDeps,
        settings: AgenticSettings | None = None,
        template: Template | None = None,
    ) -> None:
        self.deps = deps
        self.settings = settings or AgenticSettings()
        self.template = template or PromptsFactory.AGENTIC.get("agent2")

    @cached_property
    def utils(self) -> Utils:
        return Utils(deps=self.deps)

    async def retrieve(
        self,
        *_args: object,
        **_kwargs: object,
    ) -> ScoredChunks:
        return ScoredChunks([])

    async def stream_async_answer(
        self,
        query: str,
        file_ids: list[str],
        *,
        history: Sequence[UserMessage | AssistantMessage] | None = None,
        tools: list[ToolDefinition] | None = None,
        memory_md_content: str = "",
        model_name: str | None = None,
        top_k: int | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        resolved_top_k = top_k or self.settings.top_k
        resolved_model = model_name or self.settings.model_name
        if not resolved_model:
            raise ValueError("model_name is required for agentic streaming")

        actor_registry = ToolActsRegistry(
            milvus=self.deps.vectordb,
            embedding_model=self.deps.embedding_model,
            file_ids=file_ids,
            top_k=resolved_top_k,
        )

        doc_names = await self.utils.get_doc_names(file_ids)
        logger.info(
            "Retrieved doc names for given file ids",
            file_ids=file_ids,
            doc_names=doc_names,
        )

        tool_defs = tools or ToolSchemaRegistry.agentic_tools(
            internal_search=len(doc_names) > 0,
        )

        chat_request = ChatRequest(
            model=resolved_model,
            messages=[*(history or []), UserMessage(content=query)],
            tools=tool_defs,
            temperature=self.settings.temperature,
            instructions=self.template.render(
                doc_names=";".join(doc_names),
                memory_md_content=memory_md_content,
            ),
        )

        async for event in ReAct(
            streamer=self.deps.stream_provider,
            request=chat_request,
            actor_registry=actor_registry,
            max_turns=self.settings.max_turns,
        ).stream():
            yield event
