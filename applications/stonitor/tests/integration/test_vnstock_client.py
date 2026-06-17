"""Live integration tests for VnstockClient."""

from datetime import date, timedelta

import pytest

from applications.stonitor.market.exc import InvalidTickerError
from applications.stonitor.market.ingestion.vnstock_client import VnstockClient

pytestmark = [pytest.mark.external, pytest.mark.asyncio]

_CONTRACT_TICKER = "VNM"


async def test_validate_ticker_accepts_listed_symbol(
    vnstock_settings,
) -> None:
    """Listed VN tickers should validate to uppercase symbols."""
    client = VnstockClient(vnstock_settings)
    assert await client.validate_ticker("vnm") == _CONTRACT_TICKER


async def test_validate_ticker_rejects_unknown_symbol(
    vnstock_settings,
) -> None:
    """Unknown tickers should raise InvalidTickerError."""
    client = VnstockClient(vnstock_settings)
    with pytest.raises(InvalidTickerError):
        await client.validate_ticker("NOTREAL123")


async def test_fetch_ohlcv_returns_normalized_bars(
    vnstock_settings,
) -> None:
    """OHLCV response should include normalized price columns."""
    client = VnstockClient(vnstock_settings)
    end = date.today()
    start = end - timedelta(days=30)
    frame = await client.fetch_ohlcv(
        _CONTRACT_TICKER,
        start=start,
        end=end,
    )

    assert not frame.empty
    assert {"timestamp", "open", "high", "low", "close", "volume"} <= set(
        frame.columns,
    )


async def test_fetch_fundamentals_returns_known_metrics(
    vnstock_settings,
) -> None:
    """Fundamental ratios should include at least one recognized metric."""
    client = VnstockClient(vnstock_settings)
    metrics = await client.fetch_fundamentals(_CONTRACT_TICKER)

    assert isinstance(metrics, dict)
    assert any(value is not None for value in metrics.values())


async def test_fetch_news_returns_dataframe(vnstock_settings) -> None:
    """News fetch should return a DataFrame without raising."""
    client = VnstockClient(vnstock_settings)
    frame = await client.fetch_news(_CONTRACT_TICKER)
    assert frame is not None
