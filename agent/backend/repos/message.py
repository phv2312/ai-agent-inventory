from typing import Any
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.backend.db.models import MessageORM, MessageRole
from agent.backend.repos.protocols import MessageRecord


class SQLMessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        conversation_id: str,
        role: MessageRole,
        content: str,
        mapping_evidence: dict[str, str] | None = None,
        content_blocks: list[dict[str, Any]] | None = None,
    ) -> MessageRecord:
        row = MessageORM(
            conversation_id=conversation_id,
            role=role,
            content=content,
            mapping_evidence=mapping_evidence,
            content_blocks=content_blocks,
        )
        self.session.add(row)
        await self.session.flush()
        return _to_record(row)

    async def list_by_conversation(self, conversation_id: str) -> list[MessageRecord]:
        stmt = (
            select(MessageORM)
            .where(MessageORM.conversation_id == conversation_id)
            .order_by(MessageORM.created_at.asc())
        )
        rows = (await self.session.scalars(stmt)).all()
        return [_to_record(row) for row in rows]

    async def count_by_conversation(self, conversation_id: str) -> int:
        stmt = (
            select(func.count())
            .select_from(MessageORM)
            .where(MessageORM.conversation_id == conversation_id)
        )
        return int(await self.session.scalar(stmt) or 0)


def _to_record(row: MessageORM) -> MessageRecord:
    role = row.role if isinstance(row.role, MessageRole) else MessageRole(row.role)
    return MessageRecord(
        id=row.id,
        conversation_id=row.conversation_id,
        role=role,
        content=row.content,
        mapping_evidence=row.mapping_evidence,
        content_blocks=row.content_blocks,
        created_at=row.created_at,
    )
