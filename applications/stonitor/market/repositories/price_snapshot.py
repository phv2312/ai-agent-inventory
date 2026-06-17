"""Price snapshot repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from applications.stonitor.market.db.session import session_scope
from applications.stonitor.market.db.upsert import dialect_insert
from applications.stonitor.market.models.dto import (
    PriceSnapshotCreate,
    PriceSnapshotDTO,
)
from applications.stonitor.market.models.orm.price_snapshot import PriceSnapshot


def _to_dto(row: PriceSnapshot) -> PriceSnapshotDTO:
    return PriceSnapshotDTO(
        id=row.id,
        asset_id=row.asset_id,
        timestamp=row.timestamp,
        open=row.open,
        high=row.high,
        low=row.low,
        close=row.close,
        volume=row.volume,
        ingested_at=row.ingested_at,
    )


class PriceSnapshotRepository:
    """OHLCV persistence."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    async def upsert_many(self, snapshots: list[PriceSnapshotCreate]) -> int:
        if not snapshots:
            return 0
        values = [
            {
                "asset_id": snap.asset_id,
                "timestamp": snap.timestamp,
                "open": snap.open,
                "high": snap.high,
                "low": snap.low,
                "close": snap.close,
                "volume": snap.volume,
                "ingested_at": snap.ingested_at,
            }
            for snap in snapshots
        ]
        with session_scope(self._session_factory) as session:
            stmt = (
                dialect_insert(session, PriceSnapshot)
                .values(values)
                .on_conflict_do_nothing(
                    index_elements=["asset_id", "timestamp"],
                )
                .returning(PriceSnapshot.id)
            )
            inserted = session.scalars(stmt).all()
            return len(inserted)

    async def get_latest(
        self, asset_id: UUID, *, limit: int = 90
    ) -> list[PriceSnapshotDTO]:
        with session_scope(self._session_factory) as session:
            rows = session.scalars(
                select(PriceSnapshot)
                .where(PriceSnapshot.asset_id == asset_id)
                .order_by(PriceSnapshot.timestamp.desc())
                .limit(limit)
            ).all()
            return [_to_dto(row) for row in rows]
