"""Watchlist management and status rows."""

from __future__ import annotations

from datetime import UTC, datetime

from applications.stonitor.market.exc import InvalidTickerError
from applications.stonitor.market.ingestion.vnstock_client import VnstockClient
from applications.stonitor.market.models.dto import WatchlistRow
from applications.stonitor.market.models.orm.enums import SignalType
from applications.stonitor.market.repositories.protocols import (
    IAssetRepository,
    ISignalRepository,
)
from applications.stonitor.market.services.analysis import AnalysisService
from applications.stonitor.market.services.signal_utils import (
    latest_signal_batch,
)


class WatchlistService:
    """Watchlist CRUD and status columns."""

    def __init__(
        self,
        asset_repo: IAssetRepository,
        signal_repo: ISignalRepository,
        analysis: AnalysisService,
        vnstock: VnstockClient,
    ) -> None:
        self._asset_repo = asset_repo
        self._signal_repo = signal_repo
        self._analysis = analysis
        self._vnstock = vnstock

    async def list_rows(self) -> list[WatchlistRow]:
        """Return watchlist rows with trend and latest AI assessment."""
        watchlisted = await self._asset_repo.get_watchlisted()
        rows: list[WatchlistRow] = []

        for asset in watchlisted:
            signals = latest_signal_batch(
                await self._signal_repo.get_latest_for_asset(asset.id),
            )
            trend = "neutral"
            last_updated: datetime | None = None
            for signal in signals:
                if signal.signal_type == SignalType.TREND:
                    trend = signal.value
                if last_updated is None or signal.created_at > last_updated:
                    last_updated = signal.created_at

            report = await self._analysis.get_report(asset.ticker)
            severity = report.severity if report is not None else None
            stance = report.stance if report is not None else None
            if report is not None:
                last_updated = report.generated_at

            rows.append(
                WatchlistRow(
                    ticker=asset.ticker,
                    trend=trend,
                    severity=severity,
                    stance=stance,
                    last_updated=last_updated,
                ),
            )
        return rows

    async def add(self, ticker: str) -> WatchlistRow:
        """Add ticker to watchlist and start background monitoring."""
        symbol = await self._vnstock.validate_ticker(ticker)
        asset = await self._asset_repo.get_by_ticker(symbol)
        if asset is None:
            asset = await self._asset_repo.upsert(symbol, exchange=None)
        asset = await self._asset_repo.set_watchlisted(symbol, watchlisted=True)
        return WatchlistRow(
            ticker=asset.ticker,
            trend="neutral",
            severity=None,
            stance=None,
            last_updated=datetime.now(tz=UTC),
        )

    async def remove(self, ticker: str) -> None:
        """Remove ticker from watchlist and stop background monitoring."""
        symbol = ticker.strip().upper()
        asset = await self._asset_repo.get_by_ticker(symbol)
        if asset is None:
            msg = f"Asset not found: {symbol}"
            raise InvalidTickerError(msg)
        await self._asset_repo.set_watchlisted(symbol, watchlisted=False)
