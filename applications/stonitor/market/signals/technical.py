"""Technical signal computation."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import numpy as np
import pandas as pd

from applications.stonitor.market.models.dto import PriceSnapshotDTO, SignalCreate
from applications.stonitor.market.models.orm.enums import SignalCategory, SignalType

_SMA_SHORT = 20
_SMA_LONG = 50
_RSI_PERIOD = 14
_VOLATILITY_WINDOW = 20
_MIN_BARS = _SMA_LONG


def _to_price_frame(
    prices: pd.DataFrame | list[PriceSnapshotDTO],
) -> pd.DataFrame:
    if isinstance(prices, pd.DataFrame):
        frame = prices.copy()
    else:
        frame = pd.DataFrame(
            {
                "timestamp": [row.timestamp for row in prices],
                "close": [float(row.close) for row in prices],
            },
        )
    if "timestamp" not in frame.columns or "close" not in frame.columns:
        msg = "Price input must include timestamp and close columns"
        raise ValueError(msg)
    frame = frame.sort_values("timestamp").reset_index(drop=True)
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    return frame.dropna(subset=["close"])


def _compute_rsi(closes: pd.Series, period: int = _RSI_PERIOD) -> float | None:
    if len(closes) < period + 1:
        return None
    delta = closes.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    avg_gain = gains.rolling(window=period).mean().iloc[-1]
    avg_loss = losses.rolling(window=period).mean().iloc[-1]
    if pd.isna(avg_gain) or pd.isna(avg_loss):
        return None
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100 - (100 / (1 + rs)))


def _trend_value(sma_short: float, sma_long: float) -> str:
    if sma_short > sma_long * 1.01:
        return "bullish"
    if sma_short < sma_long * 0.99:
        return "bearish"
    return "neutral"


def _momentum_value(rsi: float) -> str:
    if rsi >= 70:
        return "overbought"
    if rsi <= 30:
        return "oversold"
    if rsi >= 55:
        return "positive"
    if rsi <= 45:
        return "negative"
    return "neutral"


def _volatility_value(volatility: float, baseline: float) -> str:
    if baseline <= 0:
        return "normal"
    ratio = volatility / baseline
    if ratio >= 1.5:
        return "high"
    if ratio <= 0.7:
        return "low"
    return "normal"


def compute_technical_signals(
    asset_id: UUID,
    prices: pd.DataFrame | list[PriceSnapshotDTO],
    *,
    as_of: datetime | None = None,
) -> list[SignalCreate]:
    """Compute trend, momentum, and volatility signals from price history."""
    frame = _to_price_frame(prices)
    if len(frame) < _MIN_BARS:
        return []

    created_at = as_of or datetime.now(tz=UTC)
    closes = frame["close"]
    sma_short = float(closes.rolling(_SMA_SHORT).mean().iloc[-1])
    sma_long = float(closes.rolling(_SMA_LONG).mean().iloc[-1])
    rsi = _compute_rsi(closes)
    returns = closes.pct_change().dropna()
    volatility = float(returns.tail(_VOLATILITY_WINDOW).std())
    baseline = float(returns.tail(_VOLATILITY_WINDOW * 3).std())
    if np.isnan(volatility):
        volatility = 0.0
    if np.isnan(baseline):
        baseline = volatility or 1.0

    signals: list[SignalCreate] = [
        SignalCreate(
            asset_id=asset_id,
            signal_type=SignalType.TREND,
            category=SignalCategory.TECHNICAL,
            value=_trend_value(sma_short, sma_long),
            score=sma_short - sma_long,
            confidence=min(1.0, len(frame) / (_MIN_BARS * 2)),
            evidence_json={
                "sma_20": sma_short,
                "sma_50": sma_long,
                "close": float(closes.iloc[-1]),
                "bars_used": len(frame),
            },
            created_at=created_at,
        ),
        SignalCreate(
            asset_id=asset_id,
            signal_type=SignalType.VOLATILITY,
            category=SignalCategory.TECHNICAL,
            value=_volatility_value(volatility, baseline),
            score=volatility,
            confidence=min(1.0, len(returns) / (_VOLATILITY_WINDOW * 2)),
            evidence_json={
                "rolling_std": volatility,
                "baseline_std": baseline,
                "window": _VOLATILITY_WINDOW,
            },
            created_at=created_at,
        ),
    ]
    if rsi is not None:
        signals.append(
            SignalCreate(
                asset_id=asset_id,
                signal_type=SignalType.MOMENTUM,
                category=SignalCategory.TECHNICAL,
                value=_momentum_value(rsi),
                score=rsi,
                confidence=min(1.0, len(frame) / (_RSI_PERIOD * 3)),
                evidence_json={
                    "rsi": rsi,
                    "period": _RSI_PERIOD,
                },
                created_at=created_at,
            ),
        )
    return signals
