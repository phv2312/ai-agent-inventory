import asyncio
import logging
from concurrent.futures import Executor, ThreadPoolExecutor
from typing import Any, Literal, TypedDict
from pydantic import BaseModel
from tavily import TavilyClient

from agent.models.document import ScoredChunk, ScoredChunks, Chunk, WebsearchMetdata
from agent.text_splitters import ITextSplitter, TextSplitterArguments

logger = logging.getLogger(__name__)


class SearchResult(TypedDict):
    url: str
    raw_content: str | None
    content: str | None
    title: str
    score: float


class SearchResponse(TypedDict):
    results: list[SearchResult]


class TavilySettings(BaseModel):
    chunks_per_source: int = 3
    search_depth: Literal["advanced"] = "advanced"
    timerange: Literal["day", "week", "month", "year"] = "month"

    splitter_arguments: TextSplitterArguments = TextSplitterArguments(
        chunk_size=8000,
        chunk_overlap=0,
        encoding_model_name="gpt-4o",
    )


class TavilyWebSearch:
    def __init__(
        self,
        api_key: str,
        splitter: ITextSplitter,
        executor_search: Executor | None = None,
        settings: TavilySettings | None = None,
    ) -> None:
        self.api_key = api_key
        self.client = TavilyClient(api_key)
        self.splitter = splitter
        self.executor_search = executor_search or ThreadPoolExecutor()
        self.settings = settings or TavilySettings()

    def search(
        self,
        query: str,
        topk: int = 3,
    ) -> ScoredChunks:
        if query == "":
            raise ValueError("Query cannot be empty")

        response: SearchResponse = self.client.search(
            query,
            max_results=topk,
            include_raw_content=True,  # it's necessary to get full content
            time_range=self.settings.timerange,
            chunks_per_source=self.settings.chunks_per_source,
            search_depth=self.settings.search_depth,
        )

        scored_chunks = []
        for result in response["results"]:
            if result["raw_content"] is None:
                logger.warning("Result %s has no raw content", result["url"])
                continue

            scored_chunks.append(
                ScoredChunk(
                    chunk=Chunk(
                        text=result["raw_content"] or "",
                        metadata=WebsearchMetdata(
                            url=result["url"],
                        ),
                    ),
                    score=result["score"],
                )
            )

        return ScoredChunks(scored_chunks).sort()

    async def asearch(
        self,
        query: str,
        topk: int = 3,
        *args: Any,
        **kwargs: Any,
    ) -> ScoredChunks:
        loop = asyncio.get_event_loop()
        scored_chunks = await loop.run_in_executor(
            self.executor_search, self.search, query, topk
        )
        return await scored_chunks.filter_by_tokens(
            self.splitter,
            arguments=self.settings.splitter_arguments,
        )
