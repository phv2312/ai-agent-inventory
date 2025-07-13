import asyncio
from enum import StrEnum, auto
from typing import Annotated, Literal, Self
from uuid import UUID, uuid4
from openai import BaseModel
from pydantic import BeforeValidator, ConfigDict, Field, RootModel

from agent.text_splitters import ITextSplitter, TextSplitterArguments


class Source(StrEnum):
    DOCUMENT = auto()
    WEBSEARCH = auto()


class DocumentMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")
    source: Literal[Source.DOCUMENT] = Source.DOCUMENT
    group_name: str = ""


class WebsearchMetdata(BaseModel):
    model_config = ConfigDict(extra="allow")
    source: Literal[Source.WEBSEARCH] = Source.WEBSEARCH
    url: str


Metadata = Annotated[
    DocumentMetadata | WebsearchMetdata,
    Field(
        discriminator="source",
    ),
]


class Chunk(BaseModel):
    chunk_id: UUID = Field(default_factory=uuid4)
    text: str
    metadata: Metadata


class ScoredChunk(BaseModel):
    chunk: Chunk
    score: float

    @property
    def text(self) -> str:
        return self.chunk.text

    @property
    def metadata(self) -> Metadata:
        return self.chunk.metadata


class ScoredChunks(RootModel[list[ScoredChunk]]):
    def __len__(self) -> int:
        return len(self.root)

    async def filter_by_tokens(
        self,
        text_splitter: ITextSplitter,
        arguments: TextSplitterArguments | None = None,
    ) -> Self:
        stripped_texts_list = await asyncio.gather(
            *[
                text_splitter.asplit_text(
                    scored_chunk.text,
                    arguments=arguments,
                )
                for scored_chunk in self.root
            ]
        )

        for scored_chunk, stripped_texts in zip(self.root, stripped_texts_list):
            scored_chunk.chunk.text = stripped_texts[0]

        return self

    def sort(self, reverse: bool = True) -> Self:
        self.root = sorted(self.root, key=lambda x: x.score, reverse=reverse)
        return self

    def limit(self, topk: int) -> Self:
        self.root = self.root[:topk]
        return self

    @property
    def context(self) -> str:
        contexts: list[str] = []
        traveled: dict[str, bool] = {}

        idx = 1
        for scored_chunk in self.root:
            if scored_chunk.chunk.text in traveled:
                continue
            contexts.append(f"Reference【28†[{idx}】\n{scored_chunk.chunk.text}")
            traveled[scored_chunk.chunk.text] = True
            idx += 1
        return "\n\n".join(contexts)

    def extend(self, others: list["ScoredChunks"]) -> Self:
        for other in others:
            self.root.extend(other.root)
        return self


class Document(BaseModel):
    filename: Annotated[str, BeforeValidator(lambda _input: str(_input))]
    chunks: list[Chunk]
