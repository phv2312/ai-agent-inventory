"""Integration tests for NewsIngestionService (live Tavily)."""

from __future__ import annotations

import pytest

from applications.stonitor.config import StonitorSettings
from applications.stonitor.market.ingestion.news import NewsIngestionService
from applications.stonitor.market.ingestion.tavily_client import TavilyNewsClient
from applications.stonitor.market.models.dto import AssetDTO
from applications.stonitor.market.repositories.news_article import (
    NewsArticleRepository,
)

pytestmark = [pytest.mark.external, pytest.mark.asyncio]


@pytest.fixture
def tavily_news_client() -> TavilyNewsClient:
    """Live Tavily client for news ingestion integration tests."""
    settings = StonitorSettings()
    if not settings.TAVILY_API_KEY.strip():
        pytest.skip("TAVILY_API_KEY is required for live Tavily integration tests")
    return TavilyNewsClient(settings)


@pytest.fixture
def news_ingest_service(
    tavily_news_client: TavilyNewsClient,
    news_repo: NewsArticleRepository,
) -> NewsIngestionService:
    """News ingestion wired to live Tavily."""
    return NewsIngestionService(tavily_news_client, news_repo)


async def test_ingest_persists_articles_with_sentiment(
    news_ingest_service: NewsIngestionService,
    seeded_asset: AssetDTO,
    news_repo: NewsArticleRepository,
) -> None:
    """News rows from Tavily should be upserted with sentiment scores."""
    upserted = await news_ingest_service.ingest(
        seeded_asset.id,
        seeded_asset.ticker,
    )

    rows = await news_repo.get_recent_for_asset(seeded_asset.id, days=30)
    assert len(rows) == upserted
    if upserted == 0:
        return

    for row in rows:
        assert row.title
        assert row.url
        assert -1.0 <= row.sentiment_score <= 1.0
