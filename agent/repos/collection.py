from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.db.models import CollectionORM
from agent.repos.protocols import CollectionRecord


class SQLCollectionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, name: str, description: str | None = None
    ) -> CollectionRecord:
        row = CollectionORM(name=name, description=description)
        self.session.add(row)
        await self.session.flush()
        return _to_record(row)

    async def get(self, collection_id: str) -> CollectionRecord | None:
        row = await self.session.get(CollectionORM, collection_id)
        return _to_record(row) if row else None

    async def list(self, skip: int = 0, limit: int = 20) -> list[CollectionRecord]:
        stmt = (
            select(CollectionORM)
            .order_by(CollectionORM.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        rows = (await self.session.scalars(stmt)).all()
        return [_to_record(row) for row in rows]

    async def update(
        self,
        collection_id: str,
        name: str | None = None,
        description: str | None = None,
    ) -> CollectionRecord | None:
        row = await self.session.get(CollectionORM, collection_id)
        if row is None:
            return None
        if name is not None:
            row.name = name
        if description is not None:
            row.description = description
        await self.session.flush()
        return _to_record(row)

    async def delete(self, collection_id: str) -> bool:
        result = await self.session.execute(
            delete(CollectionORM).where(CollectionORM.id == collection_id)
        )
        return result.rowcount > 0


def _to_record(row: CollectionORM) -> CollectionRecord:
    return CollectionRecord(
        id=row.id,
        name=row.name,
        description=row.description,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
