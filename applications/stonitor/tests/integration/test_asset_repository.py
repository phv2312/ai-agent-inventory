"""Integration tests for AssetRepository."""

import pytest

from applications.stonitor.market.models.orm.enums import Exchange
from applications.stonitor.market.repositories.asset import AssetRepository
from applications.stonitor.tests.integration import factories


@pytest.mark.asyncio
async def test_upsert_creates_and_updates_asset(
    asset_repo: AssetRepository,
) -> None:
    """Upsert should insert then update exchange on conflict."""
    created = await asset_repo.upsert("VNM", exchange=Exchange.HOSE.value)
    assert created.ticker == "VNM"
    assert created.exchange == Exchange.HOSE
    assert created.is_watchlisted is False

    updated = await asset_repo.upsert("vnm", exchange=Exchange.HNX.value)
    assert updated.id == created.id
    assert updated.exchange == Exchange.HNX


@pytest.mark.asyncio
async def test_set_watchlisted_and_get_watchlisted(
    asset_repo: AssetRepository,
) -> None:
    """Watchlist flag should control monitored asset listing."""
    await asset_repo.upsert("FPT", exchange=None)
    await asset_repo.upsert("VCB", exchange=None)

    await asset_repo.set_watchlisted("FPT", watchlisted=True)

    watchlisted = await asset_repo.get_watchlisted()
    tickers = {row.ticker for row in watchlisted}
    assert tickers == {"FPT"}


@pytest.mark.asyncio
async def test_remove_from_watchlist_stops_monitoring_scope(
    asset_repo: AssetRepository,
) -> None:
    """Clearing watchlist should exclude ticker from get_watchlisted."""
    await asset_repo.upsert("MWG", exchange=None)
    await asset_repo.set_watchlisted("MWG", watchlisted=True)
    await asset_repo.set_watchlisted("MWG", watchlisted=False)

    assert await asset_repo.get_watchlisted() == []
