"""Stonitor dependency injection container."""

from __future__ import annotations

from functools import cached_property

from sqlalchemy.orm import Session, sessionmaker

from agent.deps.container import Container
from agent.deps.models import ChatModel

from applications.stonitor.config import StonitorSettings
from applications.stonitor.market.db.session import build_session_factory
from applications.stonitor.market.ingestion.fundamental import (
    FundamentalIngestionService,
)
from applications.stonitor.market.ingestion.news import NewsIngestionService
from applications.stonitor.market.ingestion.price import PriceIngestionService
from applications.stonitor.market.ingestion.tavily_client import TavilyNewsClient
from applications.stonitor.market.ingestion.vnstock_client import VnstockClient
from applications.stonitor.market.jobs.scheduler import StonitorScheduler
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


class StonitorDeps:
    """Wire Container, repositories, services, and scheduler."""

    def __init__(self, settings: StonitorSettings | None = None) -> None:
        self.settings = settings or StonitorSettings()
        self.container = Container()
        self.engine, self.session_factory = build_session_factory(
            self.settings,
        )

    @cached_property
    def asset_repo(self) -> AssetRepository:
        return AssetRepository(self.session_factory)

    @cached_property
    def price_repo(self) -> PriceSnapshotRepository:
        return PriceSnapshotRepository(self.session_factory)

    @cached_property
    def news_repo(self) -> NewsArticleRepository:
        return NewsArticleRepository(self.session_factory)

    @cached_property
    def fundamental_repo(self) -> FundamentalSnapshotRepository:
        return FundamentalSnapshotRepository(self.session_factory)

    @cached_property
    def signal_repo(self) -> SignalRepository:
        return SignalRepository(self.session_factory)

    @cached_property
    def run_repo(self) -> AnalysisRunRepository:
        return AnalysisRunRepository(self.session_factory)

    @cached_property
    def vnstock(self) -> VnstockClient:
        return VnstockClient(self.settings)

    @cached_property
    def tavily_news(self) -> TavilyNewsClient:
        return TavilyNewsClient(self.settings)

    @cached_property
    def price_ingest(self) -> PriceIngestionService:
        return PriceIngestionService(self.vnstock, self.price_repo)

    @cached_property
    def news_ingest(self) -> NewsIngestionService:
        return NewsIngestionService(self.tavily_news, self.news_repo)

    @cached_property
    def fundamental_ingest(self) -> FundamentalIngestionService:
        return FundamentalIngestionService(
            self.vnstock,
            self.fundamental_repo,
        )

    @cached_property
    def registry_builder(self) -> EvidenceRegistryBuilder:
        return EvidenceRegistryBuilder()

    @cached_property
    def citation_filter(self) -> CitationFilter:
        return CitationFilter()

    @cached_property
    def report_summary_program(self) -> ReportSummaryProgram:
        chat = self.container.chats.get(ChatModel.AZURE_OPENAI)
        model_name = self.container.env.OPENAI_CHAT_DEPLOYMENT_NAME
        return ReportSummaryProgram(chat, model_name)

    @cached_property
    def report_generator(self) -> ReportGenerator:
        return ReportGenerator(
            self.registry_builder,
            self.report_summary_program,
            self.citation_filter,
        )

    @cached_property
    def evidence(self) -> EvidenceService:
        return EvidenceService(
            self.asset_repo,
            self.signal_repo,
            self.registry_builder,
        )

    @cached_property
    def analysis(self) -> AnalysisService:
        return AnalysisService(
            self.vnstock,
            self.asset_repo,
            self.price_repo,
            self.news_repo,
            self.fundamental_repo,
            self.signal_repo,
            self.run_repo,
            self.price_ingest,
            self.news_ingest,
            self.fundamental_ingest,
            self.report_generator,
            self.evidence,
        )

    @cached_property
    def watchlist(self) -> WatchlistService:
        return WatchlistService(
            self.asset_repo,
            self.signal_repo,
            self.analysis,
            self.vnstock,
        )

    @cached_property
    def scheduler(self) -> StonitorScheduler:
        return StonitorScheduler(self)

    @property
    def session_maker(self) -> sessionmaker[Session]:
        return self.session_factory
