"""Full analysis pipeline orchestration."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from uuid import UUID

from applications.stonitor.market.exc import MarketError
from applications.stonitor.market.ingestion.fundamental import (
    FundamentalIngestionService,
)
from applications.stonitor.market.ingestion.news import NewsIngestionService
from applications.stonitor.market.ingestion.price import PriceIngestionService
from applications.stonitor.market.ingestion.vnstock_client import VnstockClient
from applications.stonitor.market.logging import bind_context, get_logger
from applications.stonitor.market.models.dto import (
    AnalysisRunCreate,
    AnalysisRunDTO,
    Report,
    SignalCreate,
    SignalDTO,
)
from applications.stonitor.market.models.orm.enums import RunType
from applications.stonitor.market.reports.generator import ReportGenerator
from applications.stonitor.market.repositories.protocols import (
    IAnalysisRunRepository,
    IAssetRepository,
    IFundamentalSnapshotRepository,
    INewsArticleRepository,
    IPriceSnapshotRepository,
    ISignalRepository,
)
from applications.stonitor.market.services.evidence import EvidenceService
from applications.stonitor.market.signals import (
    article_sentiment_signals,
    compute_fundamental_signals,
    compute_technical_signals,
)

logger = get_logger(__name__)


class AnalysisService:
    """Run ingest, signals, report, and analysis run lifecycle."""

    def __init__(
        self,
        vnstock: VnstockClient,
        asset_repo: IAssetRepository,
        price_repo: IPriceSnapshotRepository,
        news_repo: INewsArticleRepository,
        fundamental_repo: IFundamentalSnapshotRepository,
        signal_repo: ISignalRepository,
        run_repo: IAnalysisRunRepository,
        price_ingest: PriceIngestionService,
        news_ingest: NewsIngestionService,
        fundamental_ingest: FundamentalIngestionService,
        report_generator: ReportGenerator,
        evidence: EvidenceService,
    ) -> None:
        self._vnstock = vnstock
        self._asset_repo = asset_repo
        self._price_repo = price_repo
        self._news_repo = news_repo
        self._fundamental_repo = fundamental_repo
        self._signal_repo = signal_repo
        self._run_repo = run_repo
        self._price_ingest = price_ingest
        self._news_ingest = news_ingest
        self._fundamental_ingest = fundamental_ingest
        self._report_generator = report_generator
        self._evidence = evidence
        self._report_cache: dict[str, Report] = {}

    async def analyze(self, ticker: str) -> Report:
        """Run full pipeline for a single ticker (one-shot, no watchlist)."""
        symbol = await self._vnstock.validate_ticker(ticker)
        bind_context(ticker=symbol, event="analyze")
        started = time.perf_counter()
        asset = await self._asset_repo.upsert(symbol, exchange=None)
        run = await self._run_repo.start(
            AnalysisRunCreate(
                asset_id=asset.id,
                run_type=RunType.ANALYSIS,
                started_at=datetime.now(tz=UTC),
            ),
        )
        try:
            await self._ingest_all(asset.id, symbol)
            signals = await self.compute_and_persist_signals(asset.id)
            report = await self._report_generator.generate(symbol, signals)
            self._report_cache[symbol] = report
            self._evidence.cache_registry(symbol, report.evidence_registry)
            duration_ms = int((time.perf_counter() - started) * 1000)
            await self._run_repo.complete(run.id, duration_ms=duration_ms)
            logger.info("analyze_complete", duration_ms=duration_ms)
            return report
        except MarketError as exc:
            await self._run_repo.fail(run.id, error_message=str(exc))
            raise
        except Exception as exc:
            await self._run_repo.fail(run.id, error_message=str(exc))
            msg = f"Analysis failed for {symbol}: {exc}"
            raise MarketError(msg) from exc

    async def get_report(self, ticker: str) -> Report | None:
        """Return latest cached report if available."""
        return self._report_cache.get(ticker.strip().upper())

    async def list_runs(self, limit: int = 50) -> list[AnalysisRunDTO]:
        """Return recent operational runs."""
        return await self._run_repo.list_recent(limit=limit)

    async def compute_and_persist_signals(
        self,
        asset_id: UUID,
    ) -> list[SignalDTO]:
        """Compute and store all signal types for an asset."""
        prices = await self._price_repo.get_latest(asset_id, limit=120)
        news = await self._news_repo.get_recent_for_asset(asset_id, days=14)
        fundamental = await self._fundamental_repo.get_latest(asset_id)
        created: list[SignalCreate] = []
        created.extend(compute_technical_signals(asset_id, prices))
        if fundamental is not None:
            created.extend(compute_fundamental_signals(fundamental))
        created.extend(article_sentiment_signals(asset_id, news))
        saved: list[SignalDTO] = []
        for signal in created:
            saved.append(await self._signal_repo.insert(signal))
        return saved

    async def _ingest_all(self, asset_id: UUID, ticker: str) -> None:
        await self._price_ingest.ingest(asset_id, ticker)
        await self._news_ingest.ingest(asset_id, ticker)
        await self._fundamental_ingest.ingest(asset_id, ticker)
