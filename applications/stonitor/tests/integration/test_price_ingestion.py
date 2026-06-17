"""Integration tests for PriceIngestionService (live vnstock)."""

from __future__ import annotations

import pytest

from applications.stonitor.market.ingestion.price import PriceIngestionService
from applications.stonitor.market.ingestion.vnstock_client import VnstockClient
from applications.stonitor.market.models.dto import AssetDTO
from applications.stonitor.market.repositories.price_snapshot import (
    PriceSnapshotRepository,
)

pytestmark = [pytest.mark.external, pytest.mark.asyncio]

_LOOKBACK_DAYS = 30


@pytest.fixture
def price_ingest_service(
    vnstock_client: VnstockClient,
    price_repo: PriceSnapshotRepository,
) -> PriceIngestionService:
    """Price ingestion wired to live vnstock."""
    return PriceIngestionService(vnstock_client, price_repo)


async def test_ingest_persists_ohlcv_rows(
    price_ingest_service: PriceIngestionService,
    seeded_asset: AssetDTO,
    price_repo: PriceSnapshotRepository,
) -> None:
    """OHLCV from vnstock should be upserted into price_snapshots."""
    inserted = await price_ingest_service.ingest(
        seeded_asset.id,
        seeded_asset.ticker,
        lookback_days=_LOOKBACK_DAYS,
    )

    assert inserted > 0
    latest = await price_repo.get_latest(seeded_asset.id, limit=500)
    assert len(latest) == inserted
    assert latest[0].close > 0


async def test_ingest_is_idempotent(
    price_ingest_service: PriceIngestionService,
    seeded_asset: AssetDTO,
    price_repo: PriceSnapshotRepository,
) -> None:
    """Re-ingesting the same bars should not create duplicates."""
    first = await price_ingest_service.ingest(
        seeded_asset.id,
        seeded_asset.ticker,
        lookback_days=_LOOKBACK_DAYS,
    )
    second = await price_ingest_service.ingest(
        seeded_asset.id,
        seeded_asset.ticker,
        lookback_days=_LOOKBACK_DAYS,
    )

    assert first > 0
    assert second == 0
    latest = await price_repo.get_latest(seeded_asset.id, limit=500)
    assert len(latest) == first
