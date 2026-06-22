import asyncio

import structlog

from agent.embeddings.interface import IEmbeddingModel
from agent.models.document import ScoredChunks
from agent.storages.vectordb.milvus import Milvus
from agent.websearches import IWebSearch


logger = structlog.get_logger(__name__)


class HybridSearch:
    def __init__(
        self,
        websearch: IWebSearch,
        milvus: Milvus,
        embedding_model: IEmbeddingModel,
    ) -> None:
        self.websearch = websearch
        self.milvus = milvus
        self.embedding_model = embedding_model

    async def semantic_search(
        self,
        query: str,
        top_k: int = 5,
    ) -> ScoredChunks:
        query_embedding = await self.embedding_model.embed([query])

        if len(query_embedding) == 0:
            raise ValueError("Query embedding is empty")

        vectordb_results = await self.milvus.search(query_embedding[0], top_k=top_k)

        logger.info(
            "Retrieve semantic results",
            count=len(vectordb_results.root),
        )

        return vectordb_results

    async def asearch(
        self, query: str, top_k: int = 5, websearch: bool = True
    ) -> ScoredChunks:
        search_tasks: list[asyncio.Task[ScoredChunks]] = [
            asyncio.create_task(self.semantic_search(query, top_k))
        ]

        if websearch:
            search_tasks.append(asyncio.create_task(self.websearch.asearch(query)))

        retrieval_list: list[ScoredChunks] = await asyncio.gather(*search_tasks)

        logger.info(
            "Retrieve hybrid results",
            result_counts=[len(retrieval) for retrieval in retrieval_list],
        )

        return ScoredChunks([]).extend(retrieval_list)
