"""Per-article news sentiment signals."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from applications.stonitor.market.models.dto import NewsArticleDTO, SignalCreate
from applications.stonitor.market.models.orm.enums import SignalCategory, SignalType


def _sentiment_label(score: float) -> str:
    if score >= 0.35:
        return "positive"
    if score <= -0.35:
        return "negative"
    return "neutral"


def article_sentiment_signals(
    asset_id: UUID,
    articles: list[NewsArticleDTO],
    *,
    as_of: datetime | None = None,
) -> list[SignalCreate]:
    """Build one news signal per article with title, content, and sentiment."""
    if not articles:
        return []

    created_at = as_of or datetime.now(tz=UTC)
    ordered = sorted(articles, key=lambda article: article.published_at, reverse=True)
    signals: list[SignalCreate] = []
    for article in ordered:
        sentiment = _sentiment_label(article.sentiment_score)
        signals.append(
            SignalCreate(
                asset_id=asset_id,
                signal_type=SignalType.SENTIMENT,
                category=SignalCategory.NEWS,
                value=sentiment,
                score=article.sentiment_score,
                confidence=min(1.0, abs(article.sentiment_score) + 0.3),
                evidence_json={
                    "title": article.title,
                    "content": article.content,
                    "day": article.published_at.date().isoformat(),
                    "sentiment": sentiment,
                    "source": article.source,
                    "url": article.url,
                },
                created_at=created_at,
            ),
        )
    return signals
