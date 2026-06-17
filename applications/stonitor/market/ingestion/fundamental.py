"""Fundamental snapshot ingestion service."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from applications.stonitor.market.ingestion.vnstock_client import VnstockClient
from applications.stonitor.market.logging import bind_context, get_logger
from applications.stonitor.market.models.dto import (
    FundamentalSnapshotCreate,
    FundamentalSnapshotDTO,
)
from applications.stonitor.market.repositories.protocols import (
    IFundamentalSnapshotRepository,
)

logger = get_logger(__name__)

_SOURCE = "vnstock/KBS"


class FundamentalIngestionService:
    """Fetch live fundamentals via vnstock and persist snapshots."""

    def __init__(
        self,
        client: VnstockClient,
        fundamental_repo: IFundamentalSnapshotRepository,
    ) -> None:
        self._client = client
        self._fundamental_repo = fundamental_repo

    async def ingest(
        self,
        asset_id: UUID,
        ticker: str,
    ) -> FundamentalSnapshotDTO:
        """Ingest latest fundamental ratios for an asset."""
        bind_context(
            ticker=ticker,
            asset_id=str(asset_id),
            event="fundamental_ingest",
        )
        metrics = await self._client.fetch_fundamentals(ticker)
        snapshot = FundamentalSnapshotCreate(
            asset_id=asset_id,
            revenue_growth=metrics.get("revenue_growth"),
            eps=metrics.get("eps"),
            net_margin=metrics.get("net_margin"),
            pe_ratio=metrics.get("pe_ratio"),
            source=_SOURCE,
            ingested_at=datetime.now(tz=UTC),
        )
        saved = await self._fundamental_repo.insert(snapshot)
        logger.info(
            "fundamental_ingest_complete",
            revenue_growth=saved.revenue_growth,
            eps=saved.eps,
            net_margin=saved.net_margin,
            pe_ratio=saved.pe_ratio,
        )
        return saved
