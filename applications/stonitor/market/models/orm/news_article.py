"""News article ORM entity."""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from applications.stonitor.market.db.base import Base

if TYPE_CHECKING:
    from applications.stonitor.market.models.orm.asset import Asset


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class NewsArticle(Base):
    """News item linked to an asset."""

    __table_args__ = (UniqueConstraint("url", name="uq_news_url"),)
    __tablename__ = "news_articles"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("assets.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=False)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    asset: Mapped["Asset"] = relationship(back_populates="news_articles")
