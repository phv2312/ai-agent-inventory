"""Integration tests for WatchlistService."""

import pytest

from applications.stonitor.market.repositories.asset import AssetRepository
from applications.stonitor.market.services.watchlist import WatchlistService


@pytest.mark.asyncio
async def test_add_places_ticker_on_watchlist_and_monitors(
    watchlist_service: WatchlistService,
    asset_repo: AssetRepository,
) -> None:
    """Adding a ticker should enable watchlist listing and monitoring."""
    row = await watchlist_service.add("FPT")

    assert row.ticker == "FPT"
    monitored = await asset_repo.get_watchlisted()
    assert [asset.ticker for asset in monitored] == ["FPT"]

    rows = await watchlist_service.list_rows()
    assert len(rows) == 1
    assert rows[0].ticker == "FPT"


@pytest.mark.asyncio
async def test_remove_stops_monitoring(
    watchlist_service: WatchlistService,
    asset_repo: AssetRepository,
) -> None:
    """Removing from watchlist should stop background monitoring scope."""
    await watchlist_service.add("HPG")
    await watchlist_service.remove("HPG")

    assert await asset_repo.get_watchlisted() == []
    assert await watchlist_service.list_rows() == []
