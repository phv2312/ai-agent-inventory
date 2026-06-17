"""Integration tests for FundamentalSnapshotRepository."""

import pytest

from applications.stonitor.market.exc import MarketError
from applications.stonitor.market.models.dto import AssetDTO
from applications.stonitor.market.repositories.fundamental_snapshot import (
    FundamentalSnapshotRepository,
)
from applications.stonitor.tests.integration import factories


@pytest.mark.asyncio
async def test_insert_and_get_latest(
    fundamental_repo: FundamentalSnapshotRepository,
    seeded_asset: AssetDTO,
) -> None:
    """Latest fundamental snapshot should match most recent insert."""
    older = factories.fundamental_snapshot_create(seeded_asset.id, pe_ratio=10.0)
    older.ingested_at = factories.utc_now().replace(year=2024, month=1, day=1)
    await fundamental_repo.insert(older)

    newer = factories.fundamental_snapshot_create(seeded_asset.id, pe_ratio=15.0)
    await fundamental_repo.insert(newer)

    latest = await fundamental_repo.get_latest(seeded_asset.id)
    assert latest is not None
    assert latest.pe_ratio == pytest.approx(15.0)


@pytest.mark.asyncio
async def test_insert_rejects_duplicate_asset_and_ingested_at(
    fundamental_repo: FundamentalSnapshotRepository,
    seeded_asset: AssetDTO,
) -> None:
    """Duplicate asset_id+ingested_at should raise MarketError."""
    snapshot = factories.fundamental_snapshot_create(seeded_asset.id)
    await fundamental_repo.insert(snapshot)

    with pytest.raises(MarketError):
        await fundamental_repo.insert(snapshot)
