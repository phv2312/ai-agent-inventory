"""Integration tests for NewsArticleRepository."""

import pytest

from applications.stonitor.market.models.dto import AssetDTO, NewsArticleCreate
from applications.stonitor.market.repositories.news_article import (
    NewsArticleRepository,
)
from applications.stonitor.tests.integration import factories


@pytest.mark.asyncio
async def test_upsert_by_url_is_idempotent(
    news_repo: NewsArticleRepository,
    seeded_asset: AssetDTO,
) -> None:
    """Same URL should update existing article instead of duplicating."""
    article = factories.news_article_create(seeded_asset.id, suffix="dup")
    first = await news_repo.upsert_by_url(article)
    updated = factories.news_article_create(
        seeded_asset.id,
        suffix="dup",
        sentiment=0.9,
    )
    second = await news_repo.upsert_by_url(updated)

    assert second.id == first.id
    assert second.sentiment_score == pytest.approx(0.9)


@pytest.mark.asyncio
async def test_get_recent_for_asset_filters_by_days(
    news_repo: NewsArticleRepository,
    seeded_asset: AssetDTO,
) -> None:
    """Recent query should include fresh articles only."""
    recent = factories.news_article_create(seeded_asset.id, suffix="recent")
    await news_repo.upsert_by_url(recent)

    stale = NewsArticleCreate(
        asset_id=seeded_asset.id,
        title="Old headline",
        source="test/source",
        url="https://example.com/news/stale",
        sentiment_score=-0.1,
        published_at=factories.utc_now().replace(year=2020, month=1, day=1),
        ingested_at=factories.utc_now(),
    )
    await news_repo.upsert_by_url(stale)

    rows = await news_repo.get_recent_for_asset(seeded_asset.id, days=7)
    urls = {row.url for row in rows}
    assert recent.url in urls
    assert stale.url not in urls
