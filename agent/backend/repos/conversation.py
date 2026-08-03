from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.backend.db.models import ConversationORM
from agent.backend.repos.protocols import ConversationRecord


class SQLConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, title: str = "") -> ConversationRecord:
        row = ConversationORM(title=title)
        self.session.add(row)
        await self.session.flush()
        return _to_record(row)

    async def get(self, conversation_id: str) -> ConversationRecord | None:
        row = await self.session.get(ConversationORM, conversation_id)
        return _to_record(row) if row else None

    async def list(self, skip: int = 0, limit: int = 20) -> list[ConversationRecord]:
        stmt = (
            select(ConversationORM)
            .order_by(ConversationORM.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        rows = (await self.session.scalars(stmt)).all()
        return [_to_record(row) for row in rows]

    async def update_title(
        self, conversation_id: str, title: str
    ) -> ConversationRecord | None:
        row = await self.session.get(ConversationORM, conversation_id)
        if row is None:
            return None
        row.title = title
        await self.session.flush()
        return _to_record(row)

    async def delete(self, conversation_id: str) -> bool:
        result = await self.session.execute(
            delete(ConversationORM).where(ConversationORM.id == conversation_id)
        )
        return result.rowcount > 0


def _to_record(row: ConversationORM) -> ConversationRecord:
    return ConversationRecord(
        id=row.id,
        title=row.title,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
