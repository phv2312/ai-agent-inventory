"""Market domain exceptions."""


class MarketError(Exception):
    """Base error for Stonitor market operations."""


class InvalidTickerError(MarketError):
    """Ticker format invalid or not listed on VN exchanges."""


class DataUnavailableError(MarketError):
    """External data source unavailable or returned empty."""


class InsufficientEvidenceError(MarketError):
    """Not enough evidence to produce a cited summary."""


class CitationNotFoundError(MarketError):
    """Citation ID not found in evidence registry."""
