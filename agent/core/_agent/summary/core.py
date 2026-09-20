from collections.abc import Sequence
from pathlib import Path
import time
from typing import Final

import structlog
from agents import Agent, ModelSettings, Runner
from agents.models.openai_responses import OpenAIResponsesModel
from agent.core.models.document import Chunk, Document

from agent.core._agent.utils import StreamUtils
from agent.core.tools import ArtifactRepository, build_summary_tools, SummaryPaths


logger = structlog.get_logger(__name__)


class AgentContainer:
    SUMMARY_INSTRUCTION: Final[str] = """
Incrementally summarize this source into reusable markdown artifacts. Keep
filenames lowercase, stable, and readable. Do not mix content from other
sources. Preserve useful prior content and do not invent unsupported facts.

Before finishing, ensure table-of-content.md exists and every link in it points
to a section file. Update sections/*.md with the relevant factual content.

Required table-of-content format:

# Table of Content

| Section | File | 1-line description |
| --- | --- | --- |
| Example | [Example](sections/example.md) | Short description |
"""

    @staticmethod
    def summarizer(
        model: OpenAIResponsesModel,
        repo: ArtifactRepository,
    ) -> Agent[None]:
        return Agent(
            name="document_summarizer",
            instructions=AgentContainer.SUMMARY_INSTRUCTION,
            model=model,
            tools=build_summary_tools(repo),
            model_settings=ModelSettings(tool_choice="required"),
        )


class DocumentSumamrizer:
    DEFAULT_TOKEN_THRESHOLD: Final[int] = 10_000

    def __init__(
        self,
        model: OpenAIResponsesModel,
        token_threshold: int = DEFAULT_TOKEN_THRESHOLD,
    ) -> None:
        self.model = model
        self.token_threshold = token_threshold

    def batch_texts(self, chunks: Sequence[Chunk]) -> list[str]:
        from langchain_core.messages.utils import count_tokens_approximately

        batches: list[str] = []
        accumulated_chunks: list[str] = []
        accumulated_tokens = 0

        for chunk in chunks:
            chunk_tokens = count_tokens_approximately(
                [{"content": chunk.text, "type": "human"}]
            )
            should_flush_batch = (
                len(accumulated_chunks) > 0
                and accumulated_tokens + chunk_tokens > self.token_threshold
            )
            if should_flush_batch:
                batches.append("\n\n".join(accumulated_chunks))
                accumulated_chunks = []
                accumulated_tokens = 0
            accumulated_chunks.append(chunk.text)
            accumulated_tokens += chunk_tokens

        if accumulated_chunks:
            batches.append("\n\n".join(accumulated_chunks))
        return batches

    async def summarize(self, doc: Document, filedir: Path) -> None:
        summary_dir = filedir / doc.fileid
        summary_dir.mkdir(parents=True, exist_ok=True)
        repo = ArtifactRepository(SummaryPaths(summary_dir))
        agent = AgentContainer.summarizer(self.model, repo)

        for idx, batched_text in enumerate(self.batch_texts(doc.chunks)):
            start_time = time.perf_counter()
            await Runner.run(agent, input=batched_text)

            events = Runner.run_streamed(agent, input=batched_text)
            await StreamUtils.print_event(events)

            logger.info(
                "summary_batch_finished",
                batch_index=idx,
                duration_seconds=time.perf_counter() - start_time,
            )

        return
