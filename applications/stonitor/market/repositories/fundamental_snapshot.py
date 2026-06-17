"""Fundamental snapshot repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from applications.stonitor.market.db.session import session_scope
from applications.stonitor.market.exc import MarketError
from applications.stonitor.market.models.dto import (
    FundamentalSnapshotCreate,
    FundamentalSnapshotDTO,
)
from applications.stonitor.market.models.orm.fundamental_snapshot import (
    FundamentalSnapshot,
)


def _to_dto(row: FundamentalSnapshot) -> FundamentalSnapshotDTO:
    return FundamentalSnapshotDTO(
        id=row.id,
        asset_id=row.asset_id,
        revenue_growth=row.revenue_growth,
        eps=row.eps,
        net_margin=row.net_margin,
        pe_ratio=row.pe_ratio,
        source=row.source,
        ingested_at=row.ingested_at,
    )


class FundamentalSnapshotRepository:
    """PostgreSQL-backed fundamental metrics persistence."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    async def insert(
        self, snapshot: FundamentalSnapshotCreate
    ) -> FundamentalSnapshotDTO:
        row = FundamentalSnapshot(
            asset_id=snapshot.asset_id,
            revenue_growth=snapshot.revenue_growth,
            eps=snapshot.eps,
            net_margin=snapshot.net_margin,
            pe_ratio=snapshot.pe_ratio,
            source=snapshot.source,
            ingested_at=snapshot.ingested_at,
        )
        with session_scope(self._session_factory) as session:
            session.add(row)
            try:
                session.flush()
            except IntegrityError as exc:
                raise MarketError(
                    "Duplicate fundamental snapshot for asset/ingested_at"
                ) from exc
            return _to_dto(row)

    async def get_latest(
        self, asset_id: UUID
    ) -> FundamentalSnapshotDTO | None:
        with session_scope(self._session_factory) as session:
            row = session.scalar(
                select(FundamentalSnapshot)
                .where(FundamentalSnapshot.asset_id == asset_id)
                .order_by(FundamentalSnapshot.ingested_at.desc())
                .limit(1)
            )
            return _to_dto(row) if row else None
