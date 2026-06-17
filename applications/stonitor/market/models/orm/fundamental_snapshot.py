"""Fundamental snapshot ORM entity."""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from applications.stonitor.market.db.base import Base

if TYPE_CHECKING:
    from applications.stonitor.market.models.orm.asset import Asset


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FundamentalSnapshot(Base):
    """Point-in-time fundamental metrics."""

    __tablename__ = "fundamental_snapshots"
    __table_args__ = (
        UniqueConstraint("asset_id", "ingested_at", name="uq_fundamental_ingest"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("assets.id"), nullable=False
    )
    revenue_growth: Mapped[float | None] = mapped_column(Float, nullable=True)
    eps: Mapped[float | None] = mapped_column(Float, nullable=True)
    net_margin: Mapped[float | None] = mapped_column(Float, nullable=True)
    pe_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    asset: Mapped["Asset"] = relationship(back_populates="fundamental_snapshots")
