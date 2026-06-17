"""Analysis run repository."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from applications.stonitor.market.db.session import session_scope
from applications.stonitor.market.exc import MarketError
from applications.stonitor.market.models.dto import (
    AnalysisRunCreate,
    AnalysisRunDTO,
)
from applications.stonitor.market.models.orm.analysis_run import AnalysisRun
from applications.stonitor.market.models.orm.asset import Asset
from applications.stonitor.market.models.orm.enums import RunStatus


def _to_dto(
    row: AnalysisRun, *, ticker: str | None = None
) -> AnalysisRunDTO:
    return AnalysisRunDTO(
        id=row.id,
        asset_id=row.asset_id,
        ticker=ticker,
        run_type=row.run_type,
        status=row.status,
        started_at=row.started_at,
        completed_at=row.completed_at,
        duration_ms=row.duration_ms,
        error_message=row.error_message,
    )


class AnalysisRunRepository:
    """PostgreSQL-backed analysis run persistence."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    async def start(self, run: AnalysisRunCreate) -> AnalysisRunDTO:
        row = AnalysisRun(
            asset_id=run.asset_id,
            run_type=run.run_type,
            started_at=run.started_at,
        )
        with session_scope(self._session_factory) as session:
            session.add(row)
            session.flush()
            ticker = None
            if run.asset_id is not None:
                ticker = session.scalar(
                    select(Asset.ticker).where(Asset.id == run.asset_id)
                )
            return _to_dto(row, ticker=ticker)

    async def complete(
        self, run_id: UUID, *, duration_ms: int
    ) -> AnalysisRunDTO:
        now = datetime.now(timezone.utc)
        with session_scope(self._session_factory) as session:
            stmt = (
                update(AnalysisRun)
                .where(AnalysisRun.id == run_id)
                .values(
                    status=RunStatus.COMPLETED,
                    completed_at=now,
                    duration_ms=duration_ms,
                )
                .returning(AnalysisRun)
            )
            row = session.scalar(stmt)
            if row is None:
                raise MarketError(f"Analysis run not found: {run_id}")
            ticker = None
            if row.asset_id is not None:
                ticker = session.scalar(
                    select(Asset.ticker).where(Asset.id == row.asset_id)
                )
            return _to_dto(row, ticker=ticker)

    async def fail(
        self, run_id: UUID, *, error_message: str
    ) -> AnalysisRunDTO:
        now = datetime.now(timezone.utc)
        with session_scope(self._session_factory) as session:
            stmt = (
                update(AnalysisRun)
                .where(AnalysisRun.id == run_id)
                .values(
                    status=RunStatus.FAILED,
                    completed_at=now,
                    error_message=error_message,
                )
                .returning(AnalysisRun)
            )
            row = session.scalar(stmt)
            if row is None:
                raise MarketError(f"Analysis run not found: {run_id}")
            ticker = None
            if row.asset_id is not None:
                ticker = session.scalar(
                    select(Asset.ticker).where(Asset.id == row.asset_id)
                )
            return _to_dto(row, ticker=ticker)

    async def list_recent(self, *, limit: int = 50) -> list[AnalysisRunDTO]:
        with session_scope(self._session_factory) as session:
            rows = session.execute(
                select(AnalysisRun, Asset.ticker)
                .outerjoin(Asset, AnalysisRun.asset_id == Asset.id)
                .order_by(AnalysisRun.started_at.desc())
                .limit(limit)
            ).all()
            return [
                _to_dto(run, ticker=ticker) for run, ticker in rows
            ]
