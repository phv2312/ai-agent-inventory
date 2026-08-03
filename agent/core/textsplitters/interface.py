from typing import Protocol

from pydantic import BaseModel


class TextSplitterArguments(BaseModel):
    chunk_size: int = 1024
    chunk_overlap: int = 256
    encoding_model_name: str = "gpt-4o"


class ITextSplitter(Protocol):
    async def asplit_text(
        self,
        text: str,
        arguments: TextSplitterArguments | None = None,
    ) -> list[str]: ...
