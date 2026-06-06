"""Indexing service: extract, embed, and store uploaded documents."""

from datetime import UTC, datetime
from pathlib import Path

from agent.deps import Container, EmbeddingModel, ExtractorModel, VectorDBModel
from agent.models.document import ScoredChunk
from agent.storages.config import AnchorFields
from applications.agentic_rag.core.models import IndexedFile
from applications.agentic_rag.core.registry import FileRegistry


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class IndexingService:
    """Extract, embed, and store uploaded documents."""

    def __init__(
        self,
        container: Container,
        registry: FileRegistry,
    ) -> None:
        self.container = container
        self.registry = registry

    async def index_file(
        self,
        filepath: Path,
        *,
        force: bool = False,
    ) -> tuple[IndexedFile, list[str]]:
        fileid = filepath.name
        existing = self.registry.get(fileid)
        if existing is not None and not force:
            return existing, [f"Skipped (already indexed): {fileid}"]

        logs: list[str] = [f"Indexing: {filepath.name}"]
        logs.append("Converting to text...")

        document = await self.container.extractors.get(
            ExtractorModel.PDF,
        ).aextract(filepath, fileid)
        logs.append(f"Extracted {len(document.chunks)} chunks")

        embeddings = await self.container.embeddings.get(
            EmbeddingModel.AZURE_OPENAI,
        ).embed([chunk.text for chunk in document.chunks])
        logs.append("Embedded chunks")

        await self.container.vectordbs.get(VectorDBModel.MILVUS).add(
            document.chunks,
            embeddings,
        )
        logs.append("Finished indexing")

        token_count = sum(estimate_tokens(c.text) for c in document.chunks)
        record = IndexedFile(
            fileid=fileid,
            name=filepath.name,
            size_bytes=filepath.stat().st_size,
            token_count=token_count,
            loader="PDFExtractor",
            date_created=datetime.now(tz=UTC),
            filepath=str(filepath),
        )
        self.registry.add(record)
        return record, logs

    async def delete_file(self, fileid: str) -> bool:
        removed = self.registry.remove(fileid)
        if removed is None:
            return False
        await self.container.vectordbs.get(
            VectorDBModel.MILVUS,
        ).delete_by_filter({AnchorFields.FILE_ID: [fileid]})
        return True

    async def get_chunks(
        self,
        fileid: str,
        *,
        chunk_filter: str = "all",
    ) -> list[ScoredChunk]:
        from agent.models.document import DocumentMetadata

        scored = await self.container.vectordbs.get(
            VectorDBModel.MILVUS,
        ).retrieve_by_filter({AnchorFields.FILE_ID: [fileid]})
        chunks = scored.root
        if chunk_filter == "text":
            chunks = [
                c for c in chunks if isinstance(c.chunk.metadata, DocumentMetadata)
            ]
        return chunks
