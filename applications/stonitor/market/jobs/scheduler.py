"""Background job scheduling for watchlisted tickers."""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from applications.stonitor.market.exc import MarketError
from applications.stonitor.market.logging import bind_context, get_logger

if TYPE_CHECKING:
    from applications.stonitor.deps import StonitorDeps

logger = get_logger(__name__)


class StonitorScheduler:
    """APScheduler wrapper for periodic watchlist analysis."""

    def __init__(self, deps: StonitorDeps) -> None:
        self._deps = deps
        self._scheduler = BackgroundScheduler()
        interval_minutes = deps.settings.ANALYZE_INTERVAL_MINUTES
        self._scheduler.add_job(
            self._watchlist_analyze_job,
            IntervalTrigger(minutes=interval_minutes),
            id="watchlist_analyze",
            replace_existing=True,
        )

    def start(self) -> None:
        """Start background scheduler."""
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("scheduler_started")

    def shutdown(self) -> None:
        """Stop background scheduler."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("scheduler_stopped")

    def _watchlist_analyze_job(self) -> None:
        asyncio.run(self._run_watchlist_analyze())

    async def _run_watchlist_analyze(self) -> None:
        for asset in await self._deps.asset_repo.get_watchlisted():
            bind_context(ticker=asset.ticker, event="job_watchlist_analyze")
            started = time.perf_counter()
            try:
                await self._deps.analysis.analyze(asset.ticker)
                duration_ms = int((time.perf_counter() - started) * 1000)
                logger.info(
                    "job_watchlist_analyze_complete",
                    duration_ms=duration_ms,
                )
            except MarketError as exc:
                logger.warning(
                    "job_watchlist_analyze_failed",
                    error=str(exc),
                )
            except Exception as exc:
                logger.exception(
                    "job_watchlist_analyze_failed",
                    error=str(exc),
                )
