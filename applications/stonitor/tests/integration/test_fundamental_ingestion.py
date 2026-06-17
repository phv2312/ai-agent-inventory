"""Integration tests for FundamentalIngestionService (live vnstock)."""

from __future__ import annotations

import pytest

from applications.stonitor.market.ingestion.fundamental import (
    FundamentalIngestionService,
)
from applications.stonitor.market.ingestion.vnstock_client import VnstockClient
from applications.stonitor.market.models.dto import AssetDTO
from applications.stonitor.market.repositories.fundamental_snapshot import (
    FundamentalSnapshotRepository,
)

pytestmark = [pytest.mark.external, pytest.mark.asyncio]


@pytest.fixture
def fundamental_ingest_service(
    vnstock_client: VnstockClient,
    fundamental_repo: FundamentalSnapshotRepository,
) -> FundamentalIngestionService:
    """Fundamental ingestion wired to live vnstock."""
    return FundamentalIngestionService(vnstock_client, fundamental_repo)


async def test_ingest_persists_fundamental_snapshot(
    fundamental_ingest_service: FundamentalIngestionService,
    seeded_asset: AssetDTO,
    fundamental_repo: FundamentalSnapshotRepository,
) -> None:
    """Live fundamentals from vnstock should be stored with attribution."""
    saved = await fundamental_ingest_service.ingest(
        seeded_asset.id,
        seeded_asset.ticker,
    )

    assert saved.source == "vnstock/KBS"
    assert any(
        value is not None
        for value in (
            saved.revenue_growth,
            saved.eps,
            saved.net_margin,
            saved.pe_ratio,
        )
    )

    latest = await fundamental_repo.get_latest(seeded_asset.id)
    assert latest is not None
    assert latest.id == saved.id
