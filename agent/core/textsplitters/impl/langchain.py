import asyncio
from concurrent.futures import Executor, ProcessPoolExecutor
from langchain_text_splitters import TokenTextSplitter
from pydantic import BaseModel

from agent.core.textsplitters.interface import TextSplitterArguments


class LangchainSplitterSettings(BaseModel):
    number_executor_split_tokens: int = 2


class LangchainTextSplitter:
    def __init__(
        self,
        settings: LangchainSplitterSettings | None = None,
        executor_split_tokens: Executor | None = None,
    ):
        self.settings = settings or LangchainSplitterSettings()
        self.executor_split_tokens = executor_split_tokens or ProcessPoolExecutor(
            max_workers=self.settings.number_executor_split_tokens
        )

    @staticmethod
    def _split_text(
        text: str,
        encoding_model_name: str,
        chunk_size: int,
        chunk_overlap: int,
    ) -> list[str]:
        return TokenTextSplitter(
            model_name=encoding_model_name,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        ).split_text(text)

    async def asplit_text(
        self,
        text: str,
        arguments: TextSplitterArguments | None = None,
    ) -> list[str]:
        arguments = arguments or TextSplitterArguments()
        loop = asyncio.get_event_loop()

        return await loop.run_in_executor(
            self.executor_split_tokens,
            self._split_text,
            text,
            arguments.encoding_model_name,
            arguments.chunk_size,
            arguments.chunk_overlap,
        )
