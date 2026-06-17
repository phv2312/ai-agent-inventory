"""Signal repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from applications.stonitor.market.db.session import session_scope
from applications.stonitor.market.models.dto import SignalCreate, SignalDTO
from applications.stonitor.market.models.orm.signal import Signal


def _to_dto(row: Signal) -> SignalDTO:
    return SignalDTO(
        id=row.id,
        asset_id=row.asset_id,
        signal_type=row.signal_type,
        category=row.category,
        value=row.value,
        score=row.score,
        confidence=row.confidence,
        evidence_json=row.evidence_json,
        created_at=row.created_at,
    )


class SignalRepository:
    """PostgreSQL-backed signal persistence."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    async def insert(self, signal: SignalCreate) -> SignalDTO:
        row = Signal(
            asset_id=signal.asset_id,
            signal_type=signal.signal_type,
            category=signal.category,
            value=signal.value,
            score=signal.score,
            confidence=signal.confidence,
            evidence_json=signal.evidence_json,
            created_at=signal.created_at,
        )
        with session_scope(self._session_factory) as session:
            session.add(row)
            session.flush()
            return _to_dto(row)

    async def get_latest_for_asset(self, asset_id: UUID) -> list[SignalDTO]:
        with session_scope(self._session_factory) as session:
            rows = session.scalars(
                select(Signal)
                .where(Signal.asset_id == asset_id)
                .order_by(Signal.created_at.desc())
            ).all()
            return [_to_dto(row) for row in rows]
