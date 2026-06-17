"""Integration tests for AnalysisRunRepository."""

import pytest

from applications.stonitor.market.models.dto import AssetDTO
from applications.stonitor.market.models.orm.enums import RunStatus, RunType
from applications.stonitor.market.repositories.analysis_run import (
    AnalysisRunRepository,
)
from applications.stonitor.tests.integration import factories


@pytest.mark.asyncio
async def test_start_complete_lifecycle(
    run_repo: AnalysisRunRepository,
    seeded_asset: AssetDTO,
) -> None:
    """Run should transition from started to completed."""
    started = await run_repo.start(
        factories.analysis_run_create(seeded_asset.id),
    )
    assert started.status == RunStatus.STARTED
    assert started.ticker == "VNM"

    completed = await run_repo.complete(started.id, duration_ms=1500)
    assert completed.status == RunStatus.COMPLETED
    assert completed.duration_ms == 1500
    assert completed.completed_at is not None


@pytest.mark.asyncio
async def test_fail_records_error_message(
    run_repo: AnalysisRunRepository,
    seeded_asset: AssetDTO,
) -> None:
    """Failed run should persist error message."""
    started = await run_repo.start(
        factories.analysis_run_create(
            seeded_asset.id,
            run_type=RunType.PRICE_INGEST,
        ),
    )

    failed = await run_repo.fail(started.id, error_message="vnstock timeout")
    assert failed.status == RunStatus.FAILED
    assert failed.error_message == "vnstock timeout"


@pytest.mark.asyncio
async def test_list_recent_orders_by_started_at_desc(
    run_repo: AnalysisRunRepository,
    seeded_asset: AssetDTO,
) -> None:
    """Recent runs should return newest first."""
    first = await run_repo.start(
        factories.analysis_run_create(seeded_asset.id),
    )
    second = await run_repo.start(
        factories.analysis_run_create(
            seeded_asset.id,
            run_type=RunType.NEWS_INGEST,
        ),
    )

    runs = await run_repo.list_recent(limit=10)
    assert [run.id for run in runs[:2]] == [second.id, first.id]
