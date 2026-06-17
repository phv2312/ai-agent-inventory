"""Test data builders for integration tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from applications.stonitor.market.models.dto import (
    AnalysisRunCreate,
    FundamentalSnapshotCreate,
    NewsArticleCreate,
    PriceSnapshotCreate,
    SignalCreate,
)
from applications.stonitor.market.models.orm.enums import (
    Exchange,
    RunType,
    SignalCategory,
    SignalType,
)


def utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(tz=UTC)


def price_snapshot_create(
    asset_id: UUID,
    *,
    day_offset: int = 0,
    close: Decimal = Decimal("100"),
    volume: int = 1_000_000,
) -> PriceSnapshotCreate:
    """Build a single OHLCV create DTO."""
    ts = utc_now() - timedelta(days=day_offset)
    return PriceSnapshotCreate(
        asset_id=asset_id,
        timestamp=ts,
        open=close,
        high=close + Decimal("1"),
        low=close - Decimal("1"),
        close=close,
        volume=volume,
        ingested_at=utc_now(),
    )


def price_series_with_volume_spike(
    asset_id: UUID,
    *,
    bar_count: int = 55,
    spike_volume: int = 50_000_000,
) -> list[PriceSnapshotCreate]:
    """Build OHLCV rows ending in a volume spike for signal tests."""
    rows = [
        price_snapshot_create(
            asset_id,
            day_offset=bar_count - index,
            close=Decimal(str(100 + index * 0.1)),
            volume=1_000_000,
        )
        for index in range(bar_count - 1)
    ]
    rows.append(
        price_snapshot_create(
            asset_id,
            day_offset=0,
            close=Decimal("105"),
            volume=spike_volume,
        ),
    )
    return rows


def news_article_create(
    asset_id: UUID,
    *,
    suffix: str = "1",
    sentiment: float = 0.2,
    content: str = "Test article body.",
) -> NewsArticleCreate:
    """Build a news article create DTO."""
    now = utc_now()
    return NewsArticleCreate(
        asset_id=asset_id,
        title=f"Test headline {suffix}",
        content=content,
        source="test/source",
        url=f"https://example.com/news/{suffix}",
        sentiment_score=sentiment,
        published_at=now - timedelta(days=1),
        ingested_at=now,
    )


def fundamental_snapshot_create(
    asset_id: UUID,
    *,
    pe_ratio: float = 12.5,
) -> FundamentalSnapshotCreate:
    """Build a fundamental snapshot create DTO."""
    return FundamentalSnapshotCreate(
        asset_id=asset_id,
        revenue_growth=0.1,
        eps=4500.0,
        net_margin=0.12,
        pe_ratio=pe_ratio,
        source="test/vnstock",
        ingested_at=utc_now(),
    )


def signal_create(
    asset_id: UUID,
    *,
    signal_type: SignalType = SignalType.TREND,
    category: SignalCategory = SignalCategory.TECHNICAL,
    value: str = "bullish",
    created_at: datetime | None = None,
) -> SignalCreate:
    """Build a signal create DTO."""
    return SignalCreate(
        asset_id=asset_id,
        signal_type=signal_type,
        category=category,
        value=value,
        score=1.0,
        confidence=0.9,
        evidence_json={"source": "test", "metric": value},
        created_at=created_at or utc_now(),
    )


def analysis_run_create(
    asset_id: UUID,
    *,
    run_type: RunType = RunType.ANALYSIS,
) -> AnalysisRunCreate:
    """Build an analysis run create DTO."""
    return AnalysisRunCreate(
        asset_id=asset_id,
        run_type=run_type,
        started_at=utc_now(),
    )


EXCHANGE_HOSE = Exchange.HOSE
