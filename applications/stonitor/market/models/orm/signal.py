"""Signal ORM entity."""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from applications.stonitor.market.db.base import Base
from applications.stonitor.market.models.orm.enums import SignalCategory, SignalType

if TYPE_CHECKING:
    from applications.stonitor.market.models.orm.asset import Asset


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Signal(Base):
    """Computed market indicator."""

    __tablename__ = "signals"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("assets.id"), nullable=False
    )
    signal_type: Mapped[SignalType] = mapped_column(
        Enum(SignalType, name="signal_type_enum", native_enum=False),
        nullable=False,
    )
    category: Mapped[SignalCategory] = mapped_column(
        Enum(SignalCategory, name="signal_category_enum", native_enum=False),
    )
    value: Mapped[str] = mapped_column(String(32), nullable=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    asset: Mapped["Asset"] = relationship(back_populates="signals")
