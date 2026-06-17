"""Thin wrapper around vnstock v4 Unified UI."""

from __future__ import annotations

import asyncio
import re
from datetime import date
from typing import Any

import pandas as pd
from vnstock import Fundamental, Market, Reference, register_user

from applications.stonitor.config import StonitorSettings
from applications.stonitor.market.exc import DataUnavailableError, InvalidTickerError

_TICKER_PATTERN = re.compile(r"^[A-Z0-9]{3,16}$")

_OHLCV_DATE_COLUMNS = ("time", "date", "trading_date", "timestamp")
_OHLCV_OPEN_COLUMNS = ("open", "o")
_OHLCV_HIGH_COLUMNS = ("high", "h")
_OHLCV_LOW_COLUMNS = ("low", "l")
_OHLCV_CLOSE_COLUMNS = ("close", "c", "price")
_OHLCV_VOLUME_COLUMNS = ("volume", "vol", "v")

_NEWS_TITLE_COLUMNS = ("title", "headline", "news_title", "tieu_de")
_NEWS_SOURCE_COLUMNS = ("source", "publisher", "news_source", "nguon")
_NEWS_URL_COLUMNS = ("url", "link", "news_url")
_NEWS_DATE_COLUMNS = ("published_at", "publish_date", "date", "time", "ngay")

_RATIO_ALIASES: dict[str, tuple[str, ...]] = {
    "revenue_growth": (
        "net_revenue",
        "revenue_growth",
        "revenue_growth_yoy",
        "doanh_thu_tang_truong",
        "tang_truong_doanh_thu",
    ),
    "eps": (
        "trailing_eps",
        "eps",
        "earning_per_share",
        "lnst_co_dong_cty_me",
    ),
    "net_margin": (
        "net_margin",
        "net_profit_margin",
        "bien_ln_rong",
        "bien_loi_nhuan_rong",
    ),
    "pe_ratio": (
        "pe_ratio",
        "price_to_earnings",
        "pe",
        "p_e",
        "he_so_pe",
    ),
}


def _year_columns(columns: pd.Index) -> list[str]:
    years = [
        str(col)
        for col in columns
        if str(col).isdigit() and len(str(col)) == 4
    ]
    return sorted(years, reverse=True)


def _is_pivot_format(df: pd.DataFrame) -> bool:
    id_col = _pick_column(df.columns, ("item_id", "item"))
    return id_col is not None and bool(_year_columns(df.columns))


def _find_metric_row(
    df: pd.DataFrame,
    *,
    id_col: str,
    aliases: tuple[str, ...],
) -> pd.Series | None:
    normalized_ids = df[id_col].astype(str).str.strip().str.lower()
    for alias in aliases:
        mask = normalized_ids == alias
        if mask.any():
            return df.loc[mask].iloc[0]
    return None


def _latest_year_value(row: pd.Series, year_cols: list[str]) -> float | None:
    for year in year_cols:
        if year not in row.index:
            continue
        value = _to_float(row[year])
        if value is not None:
            return value
    return None


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = df.copy()
    renamed.columns = [
        str(col).strip().lower().replace(" ", "_") for col in renamed.columns
    ]
    return renamed


def _pick_column(columns: pd.Index, candidates: tuple[str, ...]) -> str | None:
    for name in candidates:
        if name in columns:
            return name
    return None


def _to_float(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class VnstockClient:
    """Async-friendly wrapper for vnstock Market, Reference, Fundamental."""

    def __init__(self, settings: StonitorSettings) -> None:
        self._settings = settings
        self._registered = False
        self._listed_tickers: set[str] | None = None

    def _ensure_registered(self) -> None:
        if self._registered:
            return
        api_key = self._settings.VNSTOCK_API_KEY.strip()
        if not api_key:
            raise DataUnavailableError(
                "VNSTOCK_API_KEY is missing; live market data unavailable",
            )
        register_user(api_key=api_key)
        self._registered = True

    async def validate_ticker(self, ticker: str) -> str:
        """Return uppercase ticker if listed on VN exchanges."""
        normalized = ticker.strip().upper()
        if not _TICKER_PATTERN.match(normalized):
            msg = f"Invalid ticker format: {ticker!r}"
            raise InvalidTickerError(msg)

        listed = await self._load_listed_tickers()
        if normalized not in listed:
            msg = f"Ticker not listed on VN exchanges: {normalized}"
            raise InvalidTickerError(msg)
        return normalized

    async def fetch_ohlcv(
        self,
        ticker: str,
        *,
        start: date,
        end: date,
    ) -> pd.DataFrame:
        """Fetch normalized daily OHLCV bars."""
        symbol = await self.validate_ticker(ticker)

        def _fetch() -> pd.DataFrame:
            self._ensure_registered()
            raw = Market().equity(symbol).ohlcv(
                start=start.isoformat(),
                end=end.isoformat(),
            )
            if raw is None or raw.empty:
                msg = f"No OHLCV data for {symbol}"
                raise DataUnavailableError(msg)
            return _normalize_ohlcv(_normalize_columns(raw))

        try:
            return await asyncio.to_thread(_fetch)
        except DataUnavailableError:
            raise
        except Exception as exc:
            msg = f"vnstock OHLCV fetch failed for {symbol}: {exc}"
            raise DataUnavailableError(msg) from exc

    async def fetch_news(self, ticker: str) -> pd.DataFrame:
        """Fetch company news articles."""
        symbol = await self.validate_ticker(ticker)

        def _fetch() -> pd.DataFrame:
            self._ensure_registered()
            raw = Reference().company(symbol).news()
            if raw is None:
                return pd.DataFrame()
            return _normalize_columns(raw)

        try:
            return await asyncio.to_thread(_fetch)
        except DataUnavailableError:
            raise
        except Exception as exc:
            msg = f"vnstock news fetch failed for {symbol}: {exc}"
            raise DataUnavailableError(msg) from exc

    async def fetch_fundamentals(self, ticker: str) -> dict[str, float | None]:
        """Fetch latest fundamental ratios for a ticker."""
        symbol = await self.validate_ticker(ticker)

        def _fetch() -> dict[str, float | None]:
            self._ensure_registered()
            raw = Fundamental().equity(symbol).ratios(period="year")
            if raw is None or raw.empty:
                msg = f"No fundamental ratios for {symbol}"
                raise DataUnavailableError(msg)
            return _extract_fundamentals(_normalize_columns(raw))

        try:
            return await asyncio.to_thread(_fetch)
        except DataUnavailableError:
            raise
        except Exception as exc:
            msg = f"vnstock fundamentals fetch failed for {symbol}: {exc}"
            raise DataUnavailableError(msg) from exc

    async def _load_listed_tickers(self) -> set[str]:
        if self._listed_tickers is not None:
            return self._listed_tickers

        def _fetch() -> set[str]:
            self._ensure_registered()
            listing = Reference().equity.list()
            if listing is None or listing.empty:
                msg = "vnstock equity listing unavailable"
                raise DataUnavailableError(msg)
            normalized = _normalize_columns(listing)
            ticker_col = _pick_column(
                normalized.columns,
                ("symbol", "ticker", "code", "ma"),
            )
            if ticker_col is None:
                msg = "vnstock listing missing ticker column"
                raise DataUnavailableError(msg)
            return {
                str(value).strip().upper()
                for value in normalized[ticker_col].dropna()
            }

        try:
            self._listed_tickers = await asyncio.to_thread(_fetch)
        except DataUnavailableError:
            raise
        except Exception as exc:
            msg = f"vnstock ticker listing failed: {exc}"
            raise DataUnavailableError(msg) from exc
        return self._listed_tickers


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    date_col = _pick_column(df.columns, _OHLCV_DATE_COLUMNS)
    open_col = _pick_column(df.columns, _OHLCV_OPEN_COLUMNS)
    high_col = _pick_column(df.columns, _OHLCV_HIGH_COLUMNS)
    low_col = _pick_column(df.columns, _OHLCV_LOW_COLUMNS)
    close_col = _pick_column(df.columns, _OHLCV_CLOSE_COLUMNS)
    volume_col = _pick_column(df.columns, _OHLCV_VOLUME_COLUMNS)
    required = (date_col, open_col, high_col, low_col, close_col, volume_col)
    if any(col is None for col in required):
        msg = f"Unexpected OHLCV columns: {list(df.columns)}"
        raise DataUnavailableError(msg)

    normalized = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(df[date_col], utc=True),
            "open": pd.to_numeric(df[open_col], errors="coerce"),
            "high": pd.to_numeric(df[high_col], errors="coerce"),
            "low": pd.to_numeric(df[low_col], errors="coerce"),
            "close": pd.to_numeric(df[close_col], errors="coerce"),
            "volume": pd.to_numeric(df[volume_col], errors="coerce"),
        },
    )
    normalized = normalized.dropna()
    if normalized.empty:
        msg = "OHLCV rows empty after normalization"
        raise DataUnavailableError(msg)
    return normalized


def _normalize_percent(value: float | None) -> float | None:
    if value is None:
        return None
    if abs(value) > 1:
        return value / 100.0
    return value


def _extract_fundamentals(df: pd.DataFrame) -> dict[str, float | None]:
    if _is_pivot_format(df):
        return _extract_fundamentals_pivot(df)

    latest = df.iloc[-1]
    extracted: dict[str, float | None] = {}
    for field, aliases in _RATIO_ALIASES.items():
        column = _pick_column(df.columns, aliases)
        extracted[field] = _to_float(latest[column]) if column else None
    return _finalize_fundamentals(extracted, df)


def _extract_fundamentals_pivot(df: pd.DataFrame) -> dict[str, float | None]:
    id_col = _pick_column(df.columns, ("item_id",))
    if id_col is None:
        msg = f"Pivot fundamentals missing item_id column: {list(df.columns)}"
        raise DataUnavailableError(msg)

    year_cols = _year_columns(df.columns)
    extracted: dict[str, float | None] = {}
    for field, aliases in _RATIO_ALIASES.items():
        row = _find_metric_row(df, id_col=id_col, aliases=aliases)
        extracted[field] = (
            _latest_year_value(row, year_cols) if row is not None else None
        )
    return _finalize_fundamentals(extracted, df)


def _finalize_fundamentals(
    extracted: dict[str, float | None],
    df: pd.DataFrame,
) -> dict[str, float | None]:
    extracted["revenue_growth"] = _normalize_percent(
        extracted.get("revenue_growth"),
    )
    extracted["net_margin"] = _normalize_percent(extracted.get("net_margin"))
    if all(value is None for value in extracted.values()):
        msg = f"No recognized fundamental columns: {list(df.columns)}"
        raise DataUnavailableError(msg)
    return extracted


def news_row_fields(row: pd.Series) -> dict[str, Any]:
    """Extract normalized news fields from a vnstock news row."""
    title_col = _pick_column(row.index, _NEWS_TITLE_COLUMNS)
    source_col = _pick_column(row.index, _NEWS_SOURCE_COLUMNS)
    url_col = _pick_column(row.index, _NEWS_URL_COLUMNS)
    date_col = _pick_column(row.index, _NEWS_DATE_COLUMNS)
    if title_col is None or url_col is None:
        msg = f"Unexpected news columns: {list(row.index)}"
        raise DataUnavailableError(msg)

    published_raw = row[date_col] if date_col else None
    published_at = pd.to_datetime(published_raw, utc=True, errors="coerce")
    if pd.isna(published_at):
        msg = "News row missing publication date"
        raise DataUnavailableError(msg)

    return {
        "title": str(row[title_col]).strip(),
        "source": str(row[source_col]).strip() if source_col else "vnstock",
        "url": str(row[url_col]).strip(),
        "published_at": published_at.to_pydatetime(),
    }
