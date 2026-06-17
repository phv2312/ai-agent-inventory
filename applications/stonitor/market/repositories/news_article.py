"""News article repository."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from applications.stonitor.market.db.session import session_scope
from applications.stonitor.market.db.upsert import dialect_insert
from applications.stonitor.market.exc import MarketError
from applications.stonitor.market.models.dto import (
    NewsArticleCreate,
    NewsArticleDTO,
)
from applications.stonitor.market.models.orm.news_article import NewsArticle


def _to_dto(row: NewsArticle) -> NewsArticleDTO:
    return NewsArticleDTO(
        id=row.id,
        asset_id=row.asset_id,
        title=row.title,
        content=row.content,
        source=row.source,
        url=row.url,
        sentiment_score=row.sentiment_score,
        published_at=row.published_at,
        ingested_at=row.ingested_at,
    )


class NewsArticleRepository:
    """News article persistence."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    async def upsert_by_url(
        self, article: NewsArticleCreate
    ) -> NewsArticleDTO:
        print(article.model_dump_json(indent=2))
        with session_scope(self._session_factory) as session:
            stmt = (
                dialect_insert(session, NewsArticle)
                .values(
                    asset_id=article.asset_id,
                    title=article.title,
                    content=article.content,
                    source=article.source,
                    url=article.url,
                    sentiment_score=article.sentiment_score,
                    published_at=article.published_at,
                    ingested_at=article.ingested_at,
                )
                .on_conflict_do_update(
                    index_elements=["url"],
                    set_={
                        "asset_id": article.asset_id,
                        "title": article.title,
                        "content": article.content,
                        "source": article.source,
                        "sentiment_score": article.sentiment_score,
                        "published_at": article.published_at,
                        "ingested_at": article.ingested_at,
                    },
                )
                .returning(NewsArticle)
            )
            row = session.scalar(stmt)
            if row is None:
                existing = session.scalar(
                    select(NewsArticle).where(NewsArticle.url == article.url)
                )
                if existing is None:
                    raise MarketError(
                        f"Failed to upsert news article: {article.url}"
                    )
                return _to_dto(existing)
            return _to_dto(row)

    async def get_recent_for_asset(
        self, asset_id: UUID, *, days: int = 7
    ) -> list[NewsArticleDTO]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        with session_scope(self._session_factory) as session:
            rows = session.scalars(
                select(NewsArticle)
                .where(
                    NewsArticle.asset_id == asset_id,
                    NewsArticle.published_at >= cutoff,
                )
                .order_by(NewsArticle.published_at.desc())
            ).all()
            return [_to_dto(row) for row in rows]
