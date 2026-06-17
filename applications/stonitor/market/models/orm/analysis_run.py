"""Analysis run ORM entity."""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from applications.stonitor.market.db.base import Base
from applications.stonitor.market.models.orm.enums import RunStatus, RunType

if TYPE_CHECKING:
    from applications.stonitor.market.models.orm.asset import Asset


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AnalysisRun(Base):
    """Tracked pipeline execution."""

    __tablename__ = "analysis_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("assets.id"), nullable=True
    )
    run_type: Mapped[RunType] = mapped_column(
        Enum(RunType, name="run_type_enum", native_enum=False), nullable=False
    )
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, name="run_status_enum", native_enum=False),
        default=RunStatus.STARTED,
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    asset: Mapped["Asset | None"] = relationship(back_populates="analysis_runs")
