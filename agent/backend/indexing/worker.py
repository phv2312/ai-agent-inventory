import asyncio
from dataclasses import dataclass

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent.backend.api.container import ApiContainer
from agent.backend.db.models import IndexStatus
from agent.backend.repos.reference import SQLReferenceRepository
from agent.core.deps.models import EmbeddingModel, ExtractorModel, VectorDBModel
from agent.core.extractors.utils import materialized_file
from agent.core.models.document import DocumentMetadata

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class IndexJob:
    reference_id: str
    source_key: str
    filename: str
    collection_id: str


class IndexingWorker:
    def __init__(
        self,
        container: ApiContainer,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        consumer_count: int = 2,
    ) -> None:
        self.container = container
        self.session_factory = session_factory
        self.consumer_count = consumer_count
        self._semaphore = asyncio.Semaphore(consumer_count)

    def schedule(
        self,
        reference_id: str,
        source_key: str,
        filename: str,
        collection_id: str,
    ) -> None:
        job = IndexJob(
            reference_id=reference_id,
            source_key=source_key,
            filename=filename,
            collection_id=collection_id,
        )
        asyncio.create_task(
            self._run_job(job),
            name=f"index-{reference_id}",
        )

    async def _run_job(self, job: IndexJob) -> None:
        async with self._semaphore:
            logger.debug("Indexing job started", reference_id=job.reference_id)
            await self.arun(job)

    async def arun(self, job: IndexJob) -> None:
        async with self.session_factory() as session:
            repo = SQLReferenceRepository(session)
            await repo.update_status(job.reference_id, IndexStatus.processing)
            await session.commit()

        try:
            extractor = self.container.agent.extractors.get(ExtractorModel.PDF)
            with materialized_file(
                self.container.agent.storage,
                job.source_key,
                job.filename,
            ) as filepath:
                document = await extractor.aextract(
                    filepath,
                    fileid=job.reference_id,
                )
            embedding_model = self.container.agent.embeddings.get(
                EmbeddingModel.AZURE_OPENAI,
            )
            texts = [chunk.text for chunk in document.chunks]
            embeddings = await embedding_model.embed(texts)
            milvus = self.container.agent.vectordbs.get(VectorDBModel.MILVUS)
            for chunk in document.chunks:
                if isinstance(chunk.metadata, DocumentMetadata):
                    chunk.metadata.filename = document.filename
            if document.chunks:
                await milvus.add(document.chunks, embeddings)

            async with self.session_factory() as session:
                repo = SQLReferenceRepository(session)
                await repo.update_status(job.reference_id, IndexStatus.completed)
                await session.commit()
            logger.info(
                "Indexed reference",
                reference_id=job.reference_id,
                chunk_count=len(document.chunks),
            )
        except Exception as exc:
            logger.exception("Indexing failed", reference_id=job.reference_id)
            async with self.session_factory() as session:
                repo = SQLReferenceRepository(session)
                await repo.update_status(
                    job.reference_id,
                    IndexStatus.failed,
                    error_message=str(exc),
                )
                await session.commit()
