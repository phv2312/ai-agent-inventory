"""Asset ORM entity."""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from applications.stonitor.market.db.base import Base
from applications.stonitor.market.models.orm.enums import Exchange

if TYPE_CHECKING:
    from applications.stonitor.market.models.orm.analysis_run import AnalysisRun
    from applications.stonitor.market.models.orm.fundamental_snapshot import (
        FundamentalSnapshot,
    )
    from applications.stonitor.market.models.orm.news_article import NewsArticle
    from applications.stonitor.market.models.orm.price_snapshot import PriceSnapshot
    from applications.stonitor.market.models.orm.signal import Signal


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Asset(Base):
    """Tracked financial instrument."""

    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ticker: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    exchange: Mapped[Exchange | None] = mapped_column(
        Enum(Exchange, name="exchange_enum", native_enum=False), nullable=True
    )
    sector: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_watchlisted: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    price_snapshots: Mapped[list["PriceSnapshot"]] = relationship(
        back_populates="asset"
    )
    fundamental_snapshots: Mapped[list["FundamentalSnapshot"]] = relationship(
        back_populates="asset"
    )
    news_articles: Mapped[list["NewsArticle"]] = relationship(back_populates="asset")
    signals: Mapped[list["Signal"]] = relationship(back_populates="asset")
    analysis_runs: Mapped[list["AnalysisRun"]] = relationship(back_populates="asset")
