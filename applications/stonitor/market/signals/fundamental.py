"""Fundamental signal computation."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from applications.stonitor.market.models.dto import (
    FundamentalSnapshotDTO,
    SignalCreate,
)
from applications.stonitor.market.models.orm.enums import SignalCategory, SignalType


def _revenue_growth_signal(value: float) -> tuple[str, float]:
    if value >= 0.15:
        return "strong_growth", 1.0
    if value >= 0.05:
        return "positive", 0.6
    if value >= 0:
        return "stable", 0.2
    return "declining", -0.6


def _eps_signal(value: float) -> tuple[str, float]:
    if value >= 1000:
        return "strong", 1.0
    if value > 0:
        return "positive", 0.5
    if value == 0:
        return "neutral", 0.0
    return "negative", -0.8


def _net_margin_signal(value: float) -> tuple[str, float]:
    if value >= 0.20:
        return "high", 1.0
    if value >= 0.10:
        return "healthy", 0.6
    if value >= 0:
        return "thin", 0.1
    return "negative", -0.7


def _pe_ratio_signal(value: float) -> tuple[str, float]:
    if value <= 0:
        return "invalid", -0.5
    if value < 10:
        return "low", 0.4
    if value <= 20:
        return "moderate", 0.2
    if value <= 35:
        return "elevated", -0.1
    return "high", -0.4


def compute_fundamental_signals(
    snapshot: FundamentalSnapshotDTO,
    *,
    as_of: datetime | None = None,
) -> list[SignalCreate]:
    """Compute fundamental signals from a live-ingested snapshot."""
    created_at = as_of or datetime.now(tz=UTC)
    asset_id = snapshot.asset_id
    signals: list[SignalCreate] = []

    if snapshot.revenue_growth is not None:
        label, score = _revenue_growth_signal(snapshot.revenue_growth)
        signals.append(
            SignalCreate(
                asset_id=asset_id,
                signal_type=SignalType.FUNDAMENTAL,
                category=SignalCategory.FUNDAMENTAL,
                value=label,
                score=score,
                confidence=0.8,
                evidence_json={
                    "metric": "revenue_growth",
                    "value": snapshot.revenue_growth,
                    "source": snapshot.source,
                    "ingested_at": snapshot.ingested_at.isoformat(),
                },
                created_at=created_at,
            ),
        )

    if snapshot.eps is not None:
        label, score = _eps_signal(snapshot.eps)
        signals.append(
            SignalCreate(
                asset_id=asset_id,
                signal_type=SignalType.FUNDAMENTAL,
                category=SignalCategory.FUNDAMENTAL,
                value=label,
                score=score,
                confidence=0.8,
                evidence_json={
                    "metric": "eps",
                    "value": snapshot.eps,
                    "source": snapshot.source,
                    "ingested_at": snapshot.ingested_at.isoformat(),
                },
                created_at=created_at,
            ),
        )

    if snapshot.net_margin is not None:
        label, score = _net_margin_signal(snapshot.net_margin)
        signals.append(
            SignalCreate(
                asset_id=asset_id,
                signal_type=SignalType.FUNDAMENTAL,
                category=SignalCategory.FUNDAMENTAL,
                value=label,
                score=score,
                confidence=0.8,
                evidence_json={
                    "metric": "net_margin",
                    "value": snapshot.net_margin,
                    "source": snapshot.source,
                    "ingested_at": snapshot.ingested_at.isoformat(),
                },
                created_at=created_at,
            ),
        )

    if snapshot.pe_ratio is not None:
        label, score = _pe_ratio_signal(snapshot.pe_ratio)
        signals.append(
            SignalCreate(
                asset_id=asset_id,
                signal_type=SignalType.FUNDAMENTAL,
                category=SignalCategory.FUNDAMENTAL,
                value=label,
                score=score,
                confidence=0.75,
                evidence_json={
                    "metric": "pe_ratio",
                    "value": snapshot.pe_ratio,
                    "source": snapshot.source,
                    "ingested_at": snapshot.ingested_at.isoformat(),
                },
                created_at=created_at,
            ),
        )

    return signals
