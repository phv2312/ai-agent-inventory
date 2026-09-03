from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from agent.backend.api.settings import ApiSettings
from agent.backend.db.session import create_engine, create_session_factory, init_db
from agent.backend.repos.citation import SQLCitationRepository
from agent.backend.repos.collection import SQLCollectionRepository
from agent.backend.repos.conversation import SQLConversationRepository
from agent.backend.repos.message import SQLMessageRepository
from agent.backend.repos.pending_run import SQLPendingAgentRunRepository
from agent.backend.repos.reference import SQLReferenceRepository
from agent.backend.repos.protocols import (
    CitationRepository,
    CollectionRepository,
    ConversationRepository,
    MessageRepository,
    PendingAgentRunRepository,
    ReferenceRepository,
)
from agent.core.deps.container import Container
from agent.core.env import Env

if TYPE_CHECKING:
    from agent.backend.indexing.worker import IndexingWorker


@dataclass
class Repositories:
    conversations: ConversationRepository
    messages: MessageRepository
    citations: CitationRepository
    collections: CollectionRepository
    references: ReferenceRepository
    pending_runs: PendingAgentRunRepository


class ApiContainer:
    def __init__(self, settings: ApiSettings | None = None) -> None:
        self.settings = settings or ApiSettings()
        self.settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.engine: AsyncEngine = create_engine(self.settings.resolved_database_url())
        self.session_factory: async_sessionmaker[AsyncSession] = create_session_factory(
            self.engine
        )
        self.agent = Container(env=Env(DATA_DIR=self.settings.DATA_DIR))
        self._indexing_worker: "IndexingWorker | None" = None

    def indexing_worker(self) -> "IndexingWorker":
        if self._indexing_worker is None:
            from agent.backend.indexing.worker import IndexingWorker

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
            citations=SQLCitationRepository(session, self.settings),
            collections=SQLCollectionRepository(session),
            references=SQLReferenceRepository(session),
            pending_runs=SQLPendingAgentRunRepository(session),
        )
