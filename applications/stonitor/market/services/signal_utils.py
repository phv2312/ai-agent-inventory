"""Shared helpers for signal batch selection."""

from applications.stonitor.market.models.dto import SignalDTO


def latest_signal_batch(signals: list[SignalDTO]) -> list[SignalDTO]:
    """Return signals from the most recent computation batch."""
    if not signals:
        return []
    latest = max(signal.created_at for signal in signals)
    return [signal for signal in signals if signal.created_at == latest]
