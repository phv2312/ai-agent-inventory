import asyncio
from concurrent.futures import Executor, ProcessPoolExecutor
from pathlib import Path
from typing import Any

import pymupdf
from pydantic import BaseModel

from agent.batched import Batched
from agent.storages.local import Storage
from agent.text_splitters import (
    ITextSplitter,
    TextSplitterArguments,
)
from agent.models.document import Chunk, Document, DocumentMetadata


class PDFExtractorSettings(BaseModel):
    text_splitter_arguments: TextSplitterArguments = TextSplitterArguments(
        chunk_size=1024,
        chunk_overlap=256,
        encoding_model_name="gpt-4o",
    )
    number_executor_split_tokens: int = 2
    batch_size: int = 2


class PDFExtractor:
    def __init__(
        self,
        storage: Storage,
        text_splitter: ITextSplitter,
        settings: PDFExtractorSettings | None = None,
        executor_split_tokens: Executor | None = None,
    ):
        self.storage = storage
        self.text_splitter = text_splitter
        self.settings = settings or PDFExtractorSettings()
        self.executor_split_tokens = executor_split_tokens or ProcessPoolExecutor(
            max_workers=self.settings.number_executor_split_tokens
        )

    async def aextract(self, filepath: Path, *_: Any, **__: Any) -> Document:
        pages_content: list[str] = []
        pages_imagepath: list[str] = []
        with pymupdf.Document(filepath) as document:
            for pageidx, page in enumerate(document, start=1):
                pages_content.append(page.get_text())

                relpath = self.storage.gen_path(
                    reldir=filepath.name, name=f"page{pageidx}"
                )
                self.storage.save_image(page.get_pixmap(), relpath)
                pages_imagepath.append(relpath)

        splitted_texts_list: list[list[str]] = []
        for batched_pages_content in Batched.iter(
            pages_content, batch_size=self.settings.batch_size
        ):
            # <batch-size> pages at a time
            splitted_texts_list.extend(
                await asyncio.gather(
                    *[
                        self.text_splitter.asplit_text(
                            page_content,
                            arguments=self.settings.text_splitter_arguments,
                        )
                        for page_content in batched_pages_content
                    ]
                )
            )

        chunks = []
        for pageidx, (splitted_texts, imagepath) in enumerate(
            zip(splitted_texts_list, pages_imagepath), start=1
        ):
            chunks.extend(
                [
                    Chunk(
                        text=splitted_text,
                        metadata=DocumentMetadata(
                            group_name=str(filepath),
                        ),
                    )
                    for splitted_text in splitted_texts
                ]
            )

        return Document(
            filename=str(filepath),
            chunks=chunks,
        )
