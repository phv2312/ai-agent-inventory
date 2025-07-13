import asyncio
from functools import lru_cache
import logging
import re
from collections.abc import Sequence
from concurrent.futures import Executor, ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path
from typing import Any, Literal

import bm25s
from pydantic import BaseModel, Field

from agent.models.document import Chunk, ScoredChunk, ScoredChunks


logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_executor(
    max_workers: int = 4,
    executor_type: Literal["processpool", "threadpool"] = "processpool",
) -> Executor:
    match executor_type:
        case "threadpool":
            return ThreadPoolExecutor(max_workers=max_workers)
        case "processpool":
            return ProcessPoolExecutor(max_workers=max_workers)
        case _:
            raise ValueError(f"Unsupported executor type: {executor_type}")


class BM25SConfig(BaseModel):
    lowercase: bool = Field(default=True, description="Convert text to lowercase")

    remove_placeholders: bool = Field(
        default=True, description="Remove template placeholders like {{var}}"
    )

    max_workers: int = Field(default=4, description="Maximum number of worker")

    def preprocess_text(self, text: str) -> str:
        if self.lowercase:
            text = text.lower()

        if self.remove_placeholders:
            text = re.sub(r"\{\{.*?\}\}", " ", text)

        text = re.sub(r"\s+", " ", text).strip()

        return text


class BM25SSearchEngine:
    def __init__(
        self,
        checkpoint_dir: Path,
        config: BM25SConfig | None = None,
    ) -> None:
        self.checkpoint_dir = checkpoint_dir
        self.config = config or BM25SConfig()

        self.chunks: list[Chunk] = []
        self.retriever = bm25s.BM25()

        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.load_index()

    @property
    def index_path(self) -> Path:
        return self.checkpoint_dir / "bm25s_index"

    def load_index(self) -> None:
        if self.index_path.exists():
            try:
                self.retriever = bm25s.BM25.load(str(self.index_path), load_corpus=True)
                logger.info(
                    f"Loaded BM25S index with {len(self.retriever.corpus)} "
                    f"documents from {self.checkpoint_dir}"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to load existing index from {self.checkpoint_dir}: {e}"
                )
                self.retriever = bm25s.BM25()

    def sync_add(self, chunks: Sequence[Chunk]) -> None:
        num_chunks = len(chunks)
        if num_chunks == 0:
            logger.warning("No chunks to add to BM25S index")
            return

        logger.info(f"Adding {num_chunks} chunks to BM25S index")

        # Add
        self.chunks.extend(chunks)
        logger.info(f"Added {num_chunks} chunks. Total chunks: {len(self.chunks)}")

        # Index
        corpus_tokens = bm25s.tokenize(
            [self.config.preprocess_text(chunk.text) for chunk in self.chunks]
        )
        self.retriever.index(corpus_tokens)
        corpus_dict_list = [chunk.model_dump() for chunk in self.chunks]
        self.retriever.save(str(self.index_path), corpus=corpus_dict_list)
        self.retriever.corpus = corpus_dict_list

        logger.info("BM25S index built successfully")

    async def add(self, chunks: Sequence[Chunk]) -> None:
        # TODO: re-design for asyncio
        self.sync_add(chunks)

    @staticmethod
    def sync_search(
        query: str,
        retriever: bm25s.BM25,
        top_k: int,
        config: BM25SConfig,
    ) -> ScoredChunks:
        logger.info(f"Searching BM25S for query: '{query}' with top_k={top_k}")

        processed_query = config.preprocess_text(query)
        results_list, scores_list = retriever.retrieve(
            bm25s.tokenize([processed_query]),
            k=top_k,
        )

        if len(results_list) != 1:
            raise ValueError("BM25S search should return exactly one result set")

        if len(scores_list) != 1:
            raise ValueError("BM25S search should return exactly one score set")

        results = results_list[0]
        scores = scores_list[0]

        scored_chunks: list[ScoredChunk] = [
            ScoredChunk(
                chunk=Chunk.model_validate(corpus),
                score=score,
            )
            for corpus, score in zip(results, scores)
        ]
        return ScoredChunks(scored_chunks)

    async def search(
        self,
        query: str,
        top_k: int = 10,
        filtered_dict: dict[str, list[str | int]] | None = None,
        executor: Executor | None = None,
        **__: Any,
    ) -> ScoredChunks:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            executor or get_executor(self.config.max_workers),
            self.sync_search,
            query,
            self.retriever,
            top_k,
            self.config,
        )
