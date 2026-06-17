"""Integration tests for StonitorScheduler job handlers."""

from types import SimpleNamespace

import pytest

from applications.stonitor.market.jobs.scheduler import StonitorScheduler
from applications.stonitor.market.repositories.asset import AssetRepository


@pytest.mark.asyncio
async def test_run_watchlist_analyze_runs_for_watchlisted_asset(
    scheduler: StonitorScheduler,
    asset_repo: AssetRepository,
    scheduler_deps: SimpleNamespace,
) -> None:
    """Watchlist analyze job should run full analysis for watchlist tickers."""
    await asset_repo.upsert("FPT", exchange=None)
    await asset_repo.set_watchlisted("FPT", watchlisted=True)

    await scheduler._run_watchlist_analyze()

    scheduler_deps.analysis.analyze.assert_awaited_once_with("FPT")


@pytest.mark.asyncio
async def test_run_watchlist_analyze_skips_non_watchlisted(
    scheduler: StonitorScheduler,
    asset_repo: AssetRepository,
    scheduler_deps: SimpleNamespace,
) -> None:
    """Job should no-op when the watchlist is empty."""
    await asset_repo.upsert("VCB", exchange=None)

    await scheduler._run_watchlist_analyze()

    scheduler_deps.analysis.analyze.assert_not_awaited()


@pytest.mark.asyncio
async def test_scheduler_registers_watchlist_analyze_job(
    scheduler: StonitorScheduler,
) -> None:
    """Scheduler should register periodic watchlist analysis."""
    job_ids = {job.id for job in scheduler._scheduler.get_jobs()}
    assert job_ids == {"watchlist_analyze"}
