"""Integration tests for PriceSnapshotRepository."""

import pytest

from applications.stonitor.market.models.dto import AssetDTO
from applications.stonitor.market.repositories.price_snapshot import (
    PriceSnapshotRepository,
)
from applications.stonitor.tests.integration import factories


@pytest.mark.asyncio
async def test_upsert_many_is_idempotent(
    price_repo: PriceSnapshotRepository,
    seeded_asset: AssetDTO,
) -> None:
    """Duplicate asset_id+timestamp rows should be skipped."""
    rows = [
        factories.price_snapshot_create(seeded_asset.id, day_offset=1),
        factories.price_snapshot_create(seeded_asset.id, day_offset=2),
    ]
    first_count = await price_repo.upsert_many(rows)
    second_count = await price_repo.upsert_many(rows)

    assert first_count == 2
    assert second_count == 0

    latest = await price_repo.get_latest(seeded_asset.id, limit=10)
    assert len(latest) == 2


@pytest.mark.asyncio
async def test_get_latest_orders_by_timestamp_desc(
    price_repo: PriceSnapshotRepository,
    seeded_asset: AssetDTO,
) -> None:
    """Latest query should return newest snapshots first."""
    rows = [
        factories.price_snapshot_create(seeded_asset.id, day_offset=3),
        factories.price_snapshot_create(seeded_asset.id, day_offset=1),
        factories.price_snapshot_create(seeded_asset.id, day_offset=2),
    ]
    await price_repo.upsert_many(rows)

    latest = await price_repo.get_latest(seeded_asset.id, limit=2)
    assert len(latest) == 2
    assert latest[0].timestamp > latest[1].timestamp
