"""Asset repository."""

from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from applications.stonitor.market.db.session import session_scope
from applications.stonitor.market.db.upsert import dialect_insert
from applications.stonitor.market.exc import MarketError
from applications.stonitor.market.models.dto import AssetDTO
from applications.stonitor.market.models.orm.asset import Asset
from applications.stonitor.market.models.orm.enums import Exchange


def _to_dto(row: Asset) -> AssetDTO:
    return AssetDTO(
        id=row.id,
        ticker=row.ticker,
        exchange=row.exchange,
        sector=row.sector,
        is_watchlisted=row.is_watchlisted,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _parse_exchange(exchange: str | None) -> Exchange | None:
    if exchange is None:
        return None
    return Exchange(exchange)


class AssetRepository:
    """Asset persistence."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    async def get_by_ticker(self, ticker: str) -> AssetDTO | None:
        with session_scope(self._session_factory) as session:
            row = session.scalar(
                select(Asset).where(Asset.ticker == ticker.upper())
            )
            return _to_dto(row) if row else None

    async def get_watchlisted(self) -> list[AssetDTO]:
        with session_scope(self._session_factory) as session:
            rows = session.scalars(
                select(Asset).where(Asset.is_watchlisted.is_(True))
            ).all()
            return [_to_dto(row) for row in rows]

    async def upsert(self, ticker: str, exchange: str | None) -> AssetDTO:
        symbol = ticker.upper()
        exchange_enum = _parse_exchange(exchange)
        now = datetime.now(timezone.utc)
        with session_scope(self._session_factory) as session:
            stmt = (
                dialect_insert(session, Asset)
                .values(ticker=symbol, exchange=exchange_enum)
                .on_conflict_do_update(
                    index_elements=["ticker"],
                    set_={"exchange": exchange_enum, "updated_at": now},
                )
                .returning(Asset)
            )
            row = session.scalar(stmt)
            if row is None:
                raise MarketError(f"Failed to upsert asset: {symbol}")
            session.refresh(row)
            return _to_dto(row)

    async def set_watchlisted(
        self, ticker: str, *, watchlisted: bool
    ) -> AssetDTO:
        symbol = ticker.upper()
        now = datetime.now(timezone.utc)
        with session_scope(self._session_factory) as session:
            stmt = (
                update(Asset)
                .where(Asset.ticker == symbol)
                .values(is_watchlisted=watchlisted, updated_at=now)
                .returning(Asset)
            )
            row = session.scalar(stmt)
            if row is None:
                raise MarketError(f"Asset not found: {symbol}")
            return _to_dto(row)
