from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.backend.api.settings import ApiSettings
from agent.backend.db.models import CitationORM
from agent.backend.repos.protocols import CitationRecord


def _dedupe_snippets(snippets: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for snippet in snippets:
        if snippet in seen:
            continue
        seen.add(snippet)
        result.append(snippet)
    return result


class SQLCitationRepository:
    def __init__(
        self,
        session: AsyncSession,
        settings: ApiSettings | None = None,
    ) -> None:
        self.session = session
        self._max_snippets = (settings or ApiSettings()).MAX_SNIPPETS

    async def bulk_create(
        self,
        message_id: str,
        mp_chunk_snippets: dict[str, list[str]],
    ) -> list[CitationRecord]:
        records: list[CitationRecord] = []
        for chunk_id, snippets in mp_chunk_snippets.items():
            normalized_id = str(chunk_id).strip()
            if not normalized_id:
                continue
            deduped = _dedupe_snippets(snippets)[: self._max_snippets]
            if not deduped:
                continue
            row = CitationORM(
                message_id=message_id,
                chunk_id=normalized_id,
                snippets=deduped,
            )
            self.session.add(row)
            await self.session.flush()
            records.append(_to_record(row))
        return records

    async def get_snippets(self, message_id: str, chunk_id: str) -> list[str] | None:
        stmt = select(CitationORM).where(
            CitationORM.message_id == message_id,
            CitationORM.chunk_id == chunk_id,
        )
        row = await self.session.scalar(stmt)
        if row is None:
            return None
        return list(row.snippets)

    async def snippets_for_chunks(
        self, message_id: str, chunk_ids: list[str]
    ) -> dict[str, list[str]]:
        if not chunk_ids:
            return {}
        stmt = select(CitationORM).where(
            CitationORM.message_id == message_id,
            CitationORM.chunk_id.in_(chunk_ids),
        )
        rows = (await self.session.scalars(stmt)).all()
        return {row.chunk_id: list(row.snippets) for row in rows}

    async def list_by_message(self, message_id: str) -> list[CitationRecord]:
        stmt = (
            select(CitationORM)
            .where(CitationORM.message_id == message_id)
            .order_by(CitationORM.created_at.asc())
        )
        rows = (await self.session.scalars(stmt)).all()
        return [_to_record(row) for row in rows]


def _to_record(row: CitationORM) -> CitationRecord:
    return CitationRecord(
        id=row.id,
        message_id=row.message_id,
        chunk_id=row.chunk_id,
        snippets=list(row.snippets),
        created_at=row.created_at,
    )
