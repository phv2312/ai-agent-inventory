from enum import IntEnum
from typing import Annotated, ClassVar
from pydantic import BaseModel, Field


class EmbeddingSize(IntEnum):
    small = 1536
    large = 3072


class BaseEmbedding(BaseModel):
    size: ClassVar[int] = EmbeddingSize.small
    query: str
    embedding: Annotated[list[float], Field(min_length=size, max_length=size)]


class SmallEmbedding(BaseEmbedding):
    size = EmbeddingSize.small


Embedding = Annotated[
    SmallEmbedding,
    Field(
        discriminator="size",
    ),
]


if __name__ == "__main__":
    small_embedding = SmallEmbedding(
        query="What is the meaning of life?", embedding=[0.1] * 1536
    )
