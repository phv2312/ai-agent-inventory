"""Integration tests for AnalysisService."""

import pytest

from applications.stonitor.market.models.orm.enums import RunStatus, RunType
from applications.stonitor.market.repositories.analysis_run import (
    AnalysisRunRepository,
)
from applications.stonitor.market.repositories.asset import AssetRepository
from applications.stonitor.market.services.analysis import AnalysisService


@pytest.mark.asyncio
async def test_analyze_completes_run_and_caches_report(
    analysis_service: AnalysisService,
    run_repo: AnalysisRunRepository,
) -> None:
    """Full analyze pipeline should complete run and cache report."""
    report = await analysis_service.analyze("VNM")

    assert report.ticker == "VNM"
    assert report.ai_explanation
    assert report.severity in {"low", "medium", "high"}
    assert report.stance in {"bullish", "bearish", "neutral"}
    assert report.evidence_registry.records

    cached = await analysis_service.get_report("VNM")
    assert cached is not None
    assert cached.ticker == "VNM"

    runs = await run_repo.list_recent(limit=5)
    assert runs[0].run_type == RunType.ANALYSIS
    assert runs[0].status == RunStatus.COMPLETED
    assert runs[0].duration_ms is not None


@pytest.mark.asyncio
async def test_analyze_does_not_add_to_watchlist(
    analysis_service: AnalysisService,
    asset_repo: AssetRepository,
) -> None:
    """Analyze should remain one-shot without watchlist side effects."""
    await analysis_service.analyze("FPT")

    asset = await asset_repo.get_by_ticker("FPT")
    assert asset is not None
    assert asset.is_watchlisted is False
    assert await asset_repo.get_watchlisted() == []
