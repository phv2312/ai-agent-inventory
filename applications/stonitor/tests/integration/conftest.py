"""Shared fixtures for Stonitor integration tests."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from unittest.mock import AsyncMock

from types import SimpleNamespace

import pytest
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import delete
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from agent.deps.container import Container
from agent.deps.models import ChatModel

from applications.stonitor.config import StonitorSettings
from applications.stonitor.market.db.base import Base
from applications.stonitor.market.db.init_schema import ensure_schema
from applications.stonitor.market.db.session import (
    create_db_engine,
)
from applications.stonitor.market.ingestion.fundamental import (
    FundamentalIngestionService,
)
from applications.stonitor.market.ingestion.news import NewsIngestionService
from applications.stonitor.market.ingestion.price import PriceIngestionService
from applications.stonitor.market.ingestion.vnstock_client import VnstockClient
from applications.stonitor.market.jobs.scheduler import StonitorScheduler
from applications.stonitor.market.models.dto import (
    AssetDTO,
    CitedStatement,
    CitedSummary,
    MarketAssessment,
)
from applications.stonitor.market.programs.report_summary import (
    ReportSummaryProgram,
)
from applications.stonitor.market.reports.citation_filter import CitationFilter
from applications.stonitor.market.reports.generator import ReportGenerator
from applications.stonitor.market.reports.registry import EvidenceRegistryBuilder
from applications.stonitor.market.repositories import (
    AnalysisRunRepository,
    AssetRepository,
    FundamentalSnapshotRepository,
    NewsArticleRepository,
    PriceSnapshotRepository,
    SignalRepository,
)
from applications.stonitor.market.services.analysis import AnalysisService
from applications.stonitor.market.services.evidence import EvidenceService
from applications.stonitor.market.services.watchlist import WatchlistService
from applications.stonitor.tests.integration import factories


def _has_vnstock_key() -> bool:
    return bool(StonitorSettings().VNSTOCK_API_KEY.strip())


def _has_openai_key() -> bool:
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


@pytest.fixture
def vnstock_settings() -> StonitorSettings:
    """Stonitor settings with a configured vnstock API key."""
    if not _has_vnstock_key():
        pytest.skip("VNSTOCK_API_KEY is required for live vnstock integration tests")
    return StonitorSettings()


@pytest.fixture
def vnstock_client(vnstock_settings: StonitorSettings) -> VnstockClient:
    """Live vnstock client for ingestion integration tests."""
    return VnstockClient(vnstock_settings)


@pytest.fixture
def report_generator() -> ReportGenerator:
    """Report generator wired to the live Azure OpenAI chat model."""
    if not _has_openai_key():
        pytest.skip("OPENAI_API_KEY is required for live LLM integration tests")
    container = Container()
    chat = container.chats.get(ChatModel.AZURE_OPENAI)
    model_name = container.env.OPENAI_CHAT_DEPLOYMENT_NAME
    program = ReportSummaryProgram(chat, model_name)
    return ReportGenerator(
        EvidenceRegistryBuilder(),
        program,
        CitationFilter(),
    )


def _resolve_database_url() -> str:
    for key in ("STONITOR_TEST_DATABASE_URL", "DATABASE_URL"):
        url = os.getenv(key)
        if url:
            return url
    handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    handle.close()
    return f"sqlite:///{handle.name}"


def _truncate_all(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(delete(table))
        session.commit()


@pytest.fixture(scope="session")
def database_url() -> str:
    """Resolve integration test database URL from env or temp SQLite."""
    return _resolve_database_url()


@pytest.fixture(scope="session")
def engine(database_url: str) -> Iterator[Engine]:
    """Create engine and apply migrations once per session."""
    ensure_schema(database_url)
    db_engine = create_db_engine(database_url)
    yield db_engine
    db_engine.dispose()


@pytest.fixture(scope="session")
def session_factory(engine: Engine) -> sessionmaker[Session]:
    """Session factory bound to the test database."""
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture(autouse=True)
def clean_database(session_factory: sessionmaker[Session]) -> Iterator[None]:
    """Truncate all tables before each integration test."""
    _truncate_all(session_factory)
    yield


@pytest.fixture
def asset_repo(session_factory: sessionmaker[Session]) -> AssetRepository:
    """Asset repository wired to the test database."""
    return AssetRepository(session_factory)


@pytest.fixture
def price_repo(
    session_factory: sessionmaker[Session],
) -> PriceSnapshotRepository:
    """Price snapshot repository wired to the test database."""
    return PriceSnapshotRepository(session_factory)



@pytest.fixture
def run_repo(
    session_factory: sessionmaker[Session],
) -> AnalysisRunRepository:
    """Analysis run repository wired to the test database."""
    return AnalysisRunRepository(session_factory)


@pytest.fixture
def signal_repo(session_factory: sessionmaker[Session]) -> SignalRepository:
    """Signal repository wired to the test database."""
    return SignalRepository(session_factory)


@pytest.fixture
def news_repo(
    session_factory: sessionmaker[Session],
) -> NewsArticleRepository:
    """News article repository wired to the test database."""
    return NewsArticleRepository(session_factory)


@pytest.fixture
def fundamental_repo(
    session_factory: sessionmaker[Session],
) -> FundamentalSnapshotRepository:
    """Fundamental snapshot repository wired to the test database."""
    return FundamentalSnapshotRepository(session_factory)


@pytest.fixture
def mock_vnstock() -> VnstockClient:
    """Vnstock client that only validates tickers."""
    client = AsyncMock(spec=VnstockClient)
    client.validate_ticker = AsyncMock(
        side_effect=lambda ticker: ticker.strip().upper(),
    )
    return client


@pytest.fixture
def watchlist_service(
    asset_repo: AssetRepository,
    signal_repo: SignalRepository,
    analysis_service: AnalysisService,
    mock_vnstock: VnstockClient,
) -> WatchlistService:
    """Watchlist service with mocked vnstock validation."""
    return WatchlistService(
        asset_repo,
        signal_repo,
        analysis_service,
        mock_vnstock,
    )


@pytest.fixture
def evidence_service(
    asset_repo: AssetRepository,
    signal_repo: SignalRepository,
) -> EvidenceService:
    """Evidence service wired to real repositories."""
    return EvidenceService(
        asset_repo,
        signal_repo,
        EvidenceRegistryBuilder(),
    )


@pytest.fixture
async def seeded_asset(asset_repo: AssetRepository) -> AssetDTO:
    """Create a default asset row for foreign-key tests."""
    return await asset_repo.upsert("VNM", exchange=factories.EXCHANGE_HOSE.value)


@pytest.fixture
def analysis_service(
    asset_repo: AssetRepository,
    price_repo: PriceSnapshotRepository,
    news_repo: NewsArticleRepository,
    fundamental_repo: FundamentalSnapshotRepository,
    signal_repo: SignalRepository,
    run_repo: AnalysisRunRepository,
    evidence_service: EvidenceService,
    mock_vnstock: VnstockClient,
) -> AnalysisService:
    """Analysis service with mocked vnstock ingest and LLM summary."""
    price_ingest = AsyncMock(spec=PriceIngestionService)
    news_ingest = AsyncMock(spec=NewsIngestionService)
    fundamental_ingest = AsyncMock(spec=FundamentalIngestionService)

    async def _seed_price(asset_id, ticker: str) -> int:
        rows = factories.price_series_with_volume_spike(
            asset_id,
            bar_count=60,
            spike_volume=1_000_000,
        )
        return await price_repo.upsert_many(rows)

    async def _seed_news(asset_id, ticker: str) -> int:
        await news_repo.upsert_by_url(factories.news_article_create(asset_id))
        return 1

    async def _seed_fundamental(asset_id, ticker: str) -> int:
        await fundamental_repo.insert(
            factories.fundamental_snapshot_create(asset_id),
        )
        return 1

    price_ingest.ingest = AsyncMock(side_effect=_seed_price)
    news_ingest.ingest = AsyncMock(side_effect=_seed_news)
    fundamental_ingest.ingest = AsyncMock(side_effect=_seed_fundamental)

    summary_program = AsyncMock()
    summary_program.generate = AsyncMock(
        return_value=CitedSummary(
            assessment=MarketAssessment(
                severity="medium",
                stance="neutral",
                summary="Tín hiệu trung lập, không có biến động mạnh.",
                citation_ids=["TECH-001"],
            ),
            statements=[
                CitedStatement(
                    text="Xu hướng kỹ thuật trung tính.",
                    citation_ids=["TECH-001"],
                ),
            ],
        ),
    )

    report_generator = ReportGenerator(
        EvidenceRegistryBuilder(),
        summary_program,
        CitationFilter(),
    )

    return AnalysisService(
        mock_vnstock,
        asset_repo,
        price_repo,
        news_repo,
        fundamental_repo,
        signal_repo,
        run_repo,
        price_ingest,
        news_ingest,
        fundamental_ingest,
        report_generator,
        evidence_service,
    )


@pytest.fixture
def scheduler_deps(
    asset_repo: AssetRepository,
) -> SimpleNamespace:
    """Minimal deps bag for StonitorScheduler integration tests."""
    analysis = AsyncMock(spec=AnalysisService)
    analysis.analyze = AsyncMock()
    return SimpleNamespace(
        settings=StonitorSettings(),
        asset_repo=asset_repo,
        analysis=analysis,
    )


@pytest.fixture
def scheduler(scheduler_deps: SimpleNamespace) -> StonitorScheduler:
    """Scheduler wired to test deps."""
    return StonitorScheduler(scheduler_deps)  # type: ignore[arg-type]
