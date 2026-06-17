"""Tavily web search client for Vietnamese equity news."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from tavily import AsyncTavilyClient

from applications.stonitor.config import StonitorSettings
from applications.stonitor.market.exc import DataUnavailableError


@dataclass(frozen=True)
class NewsSearchHit:
    """Normalized news article from a Tavily search result."""

    title: str
    url: str
    source: str
    content: str
    published_at: datetime | None


def _source_from_url(url: str) -> str:
    host = urlparse(url).netloc.strip().lower()
    if host.startswith("www."):
        host = host[4:]
    return host or "tavily"


def _parse_published_at(raw: Any) -> datetime | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


class TavilyNewsClient:
    """Fetch company news via Tavily search."""

    def __init__(self, settings: StonitorSettings) -> None:
        self._settings = settings
        self._client: AsyncTavilyClient | None = None

    def _ensure_client(self) -> AsyncTavilyClient:
        api_key = self._settings.TAVILY_API_KEY.strip()
        if not api_key:
            msg = "TAVILY_API_KEY is missing; news search unavailable"
            raise DataUnavailableError(msg)
        if self._client is None:
            self._client = AsyncTavilyClient(api_key)
        return self._client

    async def fetch_news(self, ticker: str) -> list[NewsSearchHit]:
        """Search recent Vietnamese news articles for a ticker."""
        symbol = ticker.strip().upper()
        client = self._ensure_client()
        query = f"tin tức mới nhất về cổ phiếu {symbol}, tổng hợp"
        try:
            response = await client.search(
                query=query,
                search_depth="advanced",
                time_range="week",
                chunks_per_source=5,
                country="vietnam",
            )
        except Exception as exc:
            msg = f"Tavily news search failed for {symbol}: {exc}"
            raise DataUnavailableError(msg) from exc

        hits: list[NewsSearchHit] = []
        for result in response.get("results", []):
            title = str(result.get("title", "")).strip()
            url = str(result.get("url", "")).strip()
            if not title or not url:
                continue
            hits.append(
                NewsSearchHit(
                    title=title,
                    url=url,
                    source=_source_from_url(url),
                    content=str(result.get("content", "")).strip(),
                    published_at=_parse_published_at(
                        result.get("published_date"),
                    ),
                ),
            )
        return hits
