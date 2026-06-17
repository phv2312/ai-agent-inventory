"""News ingestion with deterministic sentiment scoring."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from uuid import UUID

from applications.stonitor.market.ingestion.tavily_client import TavilyNewsClient
from applications.stonitor.market.logging import bind_context, get_logger
from applications.stonitor.market.models.dto import NewsArticleCreate
from applications.stonitor.market.repositories.protocols import (
    INewsArticleRepository,
)

logger = get_logger(__name__)

_POSITIVE_TERMS = (
    "tang",
    "tang truong",
    "loi nhuan",
    "ky luc",
    "tich cuc",
    "manh",
    "thuan loi",
    "vuot",
    "dat",
    "khoi sac",
    "bullish",
    "profit",
    "growth",
    "record",
    "positive",
    "strong",
    "beat",
    "upgrade",
)

_NEGATIVE_TERMS = (
    "giam",
    "sut",
    "lo",
    "thua lo",
    "tieu cuc",
    "yeu",
    "kho khan",
    "rui ro",
    "suy giam",
    "pha san",
    "bearish",
    "loss",
    "decline",
    "negative",
    "weak",
    "miss",
    "downgrade",
    "scandal",
)

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def score_sentiment(text: str) -> float:
    """Score text sentiment in [-1.0, 1.0] using keyword lexicon."""
    tokens = _TOKEN_PATTERN.findall(text.lower())
    if not tokens:
        return 0.0

    joined = " ".join(tokens)
    positive_hits = sum(
        1 for term in _POSITIVE_TERMS if term in joined
    )
    negative_hits = sum(
        1 for term in _NEGATIVE_TERMS if term in joined
    )
    total = positive_hits + negative_hits
    if total == 0:
        return 0.0

    raw = (positive_hits - negative_hits) / total
    return max(-1.0, min(1.0, raw))


class NewsIngestionService:
    """Fetch company news and persist articles with sentiment."""

    def __init__(
        self,
        client: TavilyNewsClient,
        news_repo: INewsArticleRepository,
    ) -> None:
        self._client = client
        self._news_repo = news_repo

    async def ingest(self, asset_id: UUID, ticker: str) -> int:
        """Ingest news articles; returns count of upserted rows."""
        bind_context(ticker=ticker, asset_id=str(asset_id), event="news_ingest")
        hits = await self._client.fetch_news(ticker)
        if not hits:
            logger.info("news_ingest_empty")
            return 0

        ingested_at = datetime.now(tz=UTC)
        upserted = 0
        for hit in hits:
            sentiment = score_sentiment(f"{hit.title} {hit.content}")
            article = NewsArticleCreate(
                asset_id=asset_id,
                title=hit.title,
                content=hit.content,
                source=hit.source,
                url=hit.url,
                sentiment_score=sentiment,
                published_at=hit.published_at or ingested_at,
                ingested_at=ingested_at,
            )
            await self._news_repo.upsert_by_url(article)
            upserted += 1

        logger.info("news_ingest_complete", rows_upserted=upserted)
        return upserted
