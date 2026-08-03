import asyncio
from typing import Any
from openai import AsyncAzureOpenAI

from agent.core.batched import Batched

from agent.core.models.embeddings import SmallEmbedding, BaseEmbedding


class OpenAIEmbeddingModel[EmbeddingT: BaseEmbedding]:
    EmbeddingCls: type[EmbeddingT]

    def __init__(
        self,
        api_key: str,
        api_version: str,
        azure_endpoint: str,
        deployment_name: str,
        batch_size: int = 8,
    ) -> None:
        self.openai = AsyncAzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=azure_endpoint,
        )
        self.deployment_name = deployment_name
        self.batch_size = batch_size

    async def embed(
        self,
        queries: list[str],
        *_: Any,
        **__: Any,
    ) -> list[EmbeddingT]:
        embeddings = []
        for batched_queries in Batched.iter(queries, batch_size=self.batch_size):
            embeddings.extend(
                await asyncio.gather(
                    *[
                        self.openai.embeddings.create(
                            model=self.deployment_name,
                            input=query,
                        )
                        for query in batched_queries
                    ]
                )
            )
        return [
            self.EmbeddingCls(
                query=query,
                embedding=embedding.data[0].embedding,
            )
            for query, embedding in zip(queries, embeddings)
        ]


class SmallOpenAIEmbeddingModel(OpenAIEmbeddingModel[SmallEmbedding]):
    EmbeddingCls = SmallEmbedding
