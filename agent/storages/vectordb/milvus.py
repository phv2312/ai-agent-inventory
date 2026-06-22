from collections.abc import Sequence
from enum import StrEnum
from functools import cached_property
from typing import Any, TypedDict
from uuid import UUID, uuid4

import structlog
from pydantic import Field, BaseModel
from pymilvus import (
    AsyncMilvusClient,
    CollectionSchema,
    DataType,
    FieldSchema,
    MilvusClient,
)
from pymilvus.milvus_client.index import IndexParams

from agent.batched import Batched
from agent.models.document import Chunk, ScoredChunk, ScoredChunks
from agent.models.embeddings import BaseEmbedding, EmbeddingSize


logger = structlog.get_logger(__name__)


class RetrievedRecord(TypedDict):
    id: str
    distance: float
    entity: dict[str, Any]


class MilvusConsistency(StrEnum):
    # See https://milvus.io/docs/consistency.md#Overview
    SESSION = "Session"  # Default of llamaindex
    STRONG = "Strong"
    BOUNDED = "Bounded"
    EVENTUALLY = "Eventually"


class MilvusConfig(BaseModel):
    fieldname_id: str = Field(default="id")
    fieldname_ann_embedding: str = Field(default="embedding")
    fieldname_text: str = Field(default="text")

    dimensions: int = Field(default=EmbeddingSize.small)
    consistency: MilvusConsistency = MilvusConsistency.SESSION

    def parse_record(self, record: RetrievedRecord) -> ScoredChunk:
        params = {
            "chunk_id": UUID(record["id"]),
            "text": record["entity"][self.fieldname_text],
            "metadata": record["entity"],
        }

        return ScoredChunk(
            chunk=Chunk.model_validate(params),
            score=1.0 - record["distance"],
        )

    @property
    def id(self) -> FieldSchema:
        return FieldSchema(
            name=self.fieldname_id,
            dtype=DataType.VARCHAR,
            is_primary=True,
            auto_id=False,
            max_length=65_535,
        )

    @property
    def embedding(self) -> FieldSchema:
        return FieldSchema(
            name=self.fieldname_ann_embedding,
            dtype=DataType.FLOAT_VECTOR,
            dim=self.dimensions,
        )

    @property
    def text(self) -> FieldSchema:
        return FieldSchema(
            name=self.fieldname_text,
            dtype=DataType.VARCHAR,
            max_length=65_535,
            enable_analyzer=True,
        )

    @property
    def schema(self) -> CollectionSchema:
        schema = CollectionSchema(
            fields=[
                self.id,
                self.text,
                self.embedding,
            ],
            enable_dynamic_field=True,
        )
        return schema

    @property
    def index_params(self) -> IndexParams:
        params = IndexParams()
        params.add_index(
            field_name=self.fieldname_ann_embedding,
            index_name="ann_index",
            index_type="AUTOINDEX",
            metric_type="IP",
        )

        return params


class Milvus:
    def __init__(
        self,
        uri: str,
        collection_name: str,
        token: str = "",
        config: MilvusConfig | None = None,
        batch_sze: int = 512,
    ) -> None:
        self.uri = uri
        self.collection_name = collection_name
        self.token = token
        self.config = config or MilvusConfig()
        self.batch_size = batch_sze

        self.create_collection()

    @cached_property
    def async_client(self) -> AsyncMilvusClient:
        return AsyncMilvusClient(uri=self.uri, token=self.token, alias=str(uuid4()))

    @cached_property
    def client(self) -> MilvusClient:
        return MilvusClient(uri=self.uri, token=self.token, alias=str(uuid4()))

    def create_collection(self) -> None:
        if self.client.has_collection(self.collection_name):
            logger.info(
                "Collection already exists",
                collection_name=self.collection_name,
            )
        else:
            self.client.create_collection(
                collection_name=self.collection_name,
                schema=self.config.schema,
                index_params=self.config.index_params,
                consistency_level=self.config.consistency,
            )
            logger.info(
                "Collection created",
                collection_name=self.collection_name,
            )

        self.client.load_collection(self.collection_name)
        logger.info("Collection loaded", collection_name=self.collection_name)

    async def add(
        self, chunks: Sequence[Chunk], embeddings: Sequence[BaseEmbedding]
    ) -> None:
        num_chunk = len(chunks)
        for batched_idxs in Batched.iter(list(range(num_chunk)), self.batch_size):
            await self.async_client.insert(
                collection_name=self.collection_name,
                data=[
                    {
                        self.config.fieldname_id: str(chunks[idx].chunk_id),
                        self.config.fieldname_ann_embedding: embeddings[idx].embedding,
                        self.config.fieldname_text: chunks[idx].text,
                        **chunks[idx].metadata.model_dump(),
                    }
                    for idx in batched_idxs
                ],
            )
        logger.info(
            "Added chunks to collection",
            chunk_count=len(chunks),
            collection_name=self.collection_name,
        )

    async def retrieve_by_filter(
        self,
        filtered_dict: dict[str, Sequence[str | int]],
        *,
        limit: int = 1000,
    ) -> ScoredChunks:
        filter_expr = " and ".join(
            [f"{key} in {str(value)}" for key, value in filtered_dict.items()],
        )
        records = await self.async_client.query(
            collection_name=self.collection_name,
            filter=filter_expr,
            output_fields=["*"],
            limit=limit,
        )
        return ScoredChunks(
            [
                self.config.parse_record(
                    {
                        "id": record[self.config.fieldname_id],
                        "distance": 0.0,
                        "entity": record,
                    },
                )
                for record in records
            ],
        )

    async def search(
        self,
        query: BaseEmbedding,
        top_k: int = 10,
        filtered_dict: dict[str, Sequence[str | int]] | None = None,
    ) -> ScoredChunks:
        filter_expr = ""
        if filtered_dict:
            exprs = [f"{key} in {str(value)}" for key, value in filtered_dict.items()]
            filter_expr = " and ".join(exprs)
            logger.info("Filtering search", filter_expr=filter_expr)

        # semantic search
        searches: list[list[RetrievedRecord]] = await self.async_client.search(
            collection_name=self.collection_name,
            data=[query.embedding],
            limit=top_k,
            anns_field=self.config.fieldname_ann_embedding,
            output_fields=["*"],
            filter=filter_expr,
        )

        scored_chunks = ScoredChunks(
            [self.config.parse_record(hit) for hit in searches[0]]
        )

        return scored_chunks.sort().limit(top_k)

    async def delete_by_filter(
        self,
        filtered_dict: dict[str, Sequence[str | int]],
    ) -> None:
        filter_expr = " and ".join(
            [f"{key} in {str(value)}" for key, value in filtered_dict.items()],
        )
        await self.async_client.delete(
            collection_name=self.collection_name,
            filter=filter_expr,
        )
        logger.info(
            "Deleted chunks from collection",
            collection_name=self.collection_name,
            filter_expr=filter_expr,
        )
