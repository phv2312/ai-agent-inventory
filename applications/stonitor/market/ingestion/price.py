"""Price snapshot ingestion service."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from applications.stonitor.market.ingestion.vnstock_client import VnstockClient
from applications.stonitor.market.logging import bind_context, get_logger
from applications.stonitor.market.models.dto import PriceSnapshotCreate
from applications.stonitor.market.repositories.protocols import (
    IPriceSnapshotRepository,
)

logger = get_logger(__name__)

_DEFAULT_LOOKBACK_DAYS = 120


class PriceIngestionService:
    """Fetch OHLCV via vnstock and persist price snapshots."""

    def __init__(
        self,
        client: VnstockClient,
        price_repo: IPriceSnapshotRepository,
    ) -> None:
        self._client = client
        self._price_repo = price_repo

    async def ingest(
        self,
        asset_id: UUID,
        ticker: str,
        *,
        lookback_days: int = _DEFAULT_LOOKBACK_DAYS,
    ) -> int:
        """Ingest OHLCV rows for an asset; returns new row count."""
        bind_context(ticker=ticker, asset_id=str(asset_id), event="price_ingest")
        end = date.today()
        start = end - timedelta(days=lookback_days)
        ohlcv = await self._client.fetch_ohlcv(ticker, start=start, end=end)
        ingested_at = datetime.now(tz=UTC)
        snapshots = [
            PriceSnapshotCreate(
                asset_id=asset_id,
                timestamp=row["timestamp"].to_pydatetime(),
                open=Decimal(str(row["open"])),
                high=Decimal(str(row["high"])),
                low=Decimal(str(row["low"])),
                close=Decimal(str(row["close"])),
                volume=int(row["volume"]),
                ingested_at=ingested_at,
            )
            for _, row in ohlcv.iterrows()
        ]
        inserted = await self._price_repo.upsert_many(snapshots)
        logger.info(
            "price_ingest_complete",
            rows_fetched=len(snapshots),
            rows_inserted=inserted,
        )
        return inserted
