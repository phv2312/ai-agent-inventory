import asyncio
from concurrent.futures import Executor, ProcessPoolExecutor
from pathlib import Path
from typing import Any

import pymupdf
from pymupdf4llm import to_markdown
from pydantic import BaseModel

from agent.core.batched import Batched
from agent.core.storages.files.exporter import ReferenceExporter
from agent.core.storages.files.interface import IFileStorage
from agent.core.textsplitters import (
    ITextSplitter,
    TextSplitterArguments,
)
from agent.core.models.document import Chunk, Document, DocumentMetadata


class PDFExtractorSettings(BaseModel):
    text_splitter_arguments: TextSplitterArguments = TextSplitterArguments(
        chunk_size=7800,
        chunk_overlap=256,
        encoding_model_name="gpt-4o",
    )
    number_executor_split_tokens: int = 2
    batch_size: int = 2


class PDFExtractor:
    def __init__(
        self,
        storage: IFileStorage,
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

    async def aextract(
        self, filepath: Path, fileid: str, *_: Any, **__: Any
    ) -> Document:
        pages_content: list[str] = []
        pages_imagepath: list[str] = []
        exporter = ReferenceExporter(fileid)
        with pymupdf.Document(filepath) as document:
            for pageidx, page in enumerate(document, start=1):
                pages_content.append(to_markdown(document, pages=[pageidx - 1]))
                image_key = exporter.rendered_page_key(pageidx)
                self.storage.write_bytes(image_key, page.get_pixmap().tobytes("png"))
                pages_imagepath.append(image_key)

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
        for pageidx, (splitted_texts, image_key) in enumerate(
            zip(splitted_texts_list, pages_imagepath), start=1
        ):
            chunks.extend(
                [
                    Chunk(
                        text=splitted_text,
                        metadata=DocumentMetadata(
                            filename=str(filepath.name),
                            pageidx=pageidx,
                            rendered_page_path=image_key,
                            fileid=fileid,
                        ),
                    )
                    for splitted_text in splitted_texts
                ]
            )

        return Document(
            filename=str(filepath.name),
            fileid=fileid,
            chunks=chunks,
        )
