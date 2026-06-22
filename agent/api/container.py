from dataclasses import dataclass
from typing import TYPE_CHECKING
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from agent.api.settings import ApiSettings
from agent.deps.container import Container
from agent.db.session import create_engine, create_session_factory, init_db
from agent.repos.collection import SQLCollectionRepository
from agent.repos.conversation import SQLConversationRepository
from agent.repos.message import SQLMessageRepository
from agent.repos.reference import SQLReferenceRepository
from agent.repos.protocols import (
    CollectionRepository,
    ConversationRepository,
    MessageRepository,
    ReferenceRepository,
)

if TYPE_CHECKING:
    from agent.services.indexing.worker import IndexingWorker


@dataclass
class Repositories:
    conversations: ConversationRepository
    messages: MessageRepository
    collections: CollectionRepository
    references: ReferenceRepository


class ApiContainer:
    def __init__(self, settings: ApiSettings | None = None) -> None:
        self.settings = settings or ApiSettings()
        self.settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
        (self.settings.DATA_DIR / "references").mkdir(parents=True, exist_ok=True)
        self.engine: AsyncEngine = create_engine(self.settings.resolved_database_url())
        self.session_factory: async_sessionmaker[AsyncSession] = create_session_factory(
            self.engine
        )
        self.agent = Container()
        ref_images = self.settings.DATA_DIR / "images"
        ref_images.mkdir(parents=True, exist_ok=True)
        from agent.storages.file import FileStorage

        self.agent.storage = FileStorage(imagedir=ref_images)
        self._indexing_worker: "IndexingWorker | None" = None

    def indexing_worker(self) -> "IndexingWorker":
        if self._indexing_worker is None:
            from agent.services.indexing.worker import IndexingWorker

            self._indexing_worker = IndexingWorker(
                self,
                self.session_factory,
                consumer_count=self.settings.INDEXING_CONSUMER_COUNT,
            )
        return self._indexing_worker

    async def startup(self) -> None:
        await init_db(self.engine)

    async def shutdown(self) -> None:
        await self.engine.dispose()

    def repos(self, session: AsyncSession) -> Repositories:
        return Repositories(
            conversations=SQLConversationRepository(session),
            messages=SQLMessageRepository(session),
            collections=SQLCollectionRepository(session),
            references=SQLReferenceRepository(session),
        )

    @property
    def references_dir(self) -> Path:
        return self.settings.DATA_DIR / "references"
