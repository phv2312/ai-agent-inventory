from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from agent.backend.db.models import PendingAgentRunORM
from agent.backend.repos.protocols import PendingAgentRunRecord


class SQLPendingAgentRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        conversation_id: str,
        user_message_id: str,
        state_json: str,
        request_snapshot: dict[str, Any],
        interruptions: list[dict[str, Any]],
    ) -> PendingAgentRunRecord:
        row = PendingAgentRunORM(
            conversation_id=conversation_id,
            user_message_id=user_message_id,
            state_json=state_json,
            request_snapshot=request_snapshot,
            interruptions=interruptions,
        )
        self.session.add(row)
        await self.session.flush()
        return _to_record(row)

    async def get(self, conversation_id: str) -> PendingAgentRunRecord | None:
        row = await self.session.get(PendingAgentRunORM, conversation_id)
        return _to_record(row) if row is not None else None

    async def replace(
        self,
        *,
        conversation_id: str,
        version: int,
        state_json: str,
        interruptions: list[dict[str, Any]],
    ) -> PendingAgentRunRecord | None:
        stmt = (
            update(PendingAgentRunORM)
            .where(
                PendingAgentRunORM.conversation_id == conversation_id,
                PendingAgentRunORM.version == version,
            )
            .values(
                state_json=state_json,
                interruptions=interruptions,
                version=version + 1,
                updated_at=datetime.now(UTC),
            )
        )
        result = await self.session.execute(stmt)
        assert isinstance(result, CursorResult)
        if result.rowcount != 1:
            return None
        await self.session.flush()
        return await self.get(conversation_id)

    async def delete(self, conversation_id: str, version: int) -> bool:
        stmt = delete(PendingAgentRunORM).where(
            PendingAgentRunORM.conversation_id == conversation_id,
            PendingAgentRunORM.version == version,
        )
        result = await self.session.execute(stmt)
        assert isinstance(result, CursorResult)
        return result.rowcount == 1


def _to_record(row: PendingAgentRunORM) -> PendingAgentRunRecord:
    return PendingAgentRunRecord(
        conversation_id=row.conversation_id,
        user_message_id=row.user_message_id,
        state_json=row.state_json,
        request_snapshot=row.request_snapshot,
        interruptions=row.interruptions,
        version=row.version,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
