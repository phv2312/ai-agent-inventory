from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.db.models import IndexStatus, ReferenceORM
from agent.repos.protocols import ReferenceRecord


class SQLReferenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        collection_id: str,
        doc_name: str,
        filename: str,
        content_type: str,
        file_path: str,
        metadata_json: dict[str, object] | None = None,
    ) -> ReferenceRecord:
        row = ReferenceORM(
            collection_id=collection_id,
            doc_name=doc_name,
            filename=filename,
            content_type=content_type,
            file_path=file_path,
            metadata_json=metadata_json,
            status=IndexStatus.pending,
        )
        self.session.add(row)
        await self.session.flush()
        return _to_record(row)

    async def get(self, reference_id: str) -> ReferenceRecord | None:
        row = await self.session.get(ReferenceORM, reference_id)
        return _to_record(row) if row else None

    async def list_by_collection(self, collection_id: str) -> list[ReferenceRecord]:
        stmt = (
            select(ReferenceORM)
            .where(ReferenceORM.collection_id == collection_id)
            .order_by(ReferenceORM.created_at.desc())
        )
        rows = (await self.session.scalars(stmt)).all()
        return [_to_record(row) for row in rows]

    async def update_status(
        self,
        reference_id: str,
        status: IndexStatus,
        error_message: str | None = None,
    ) -> ReferenceRecord | None:
        row = await self.session.get(ReferenceORM, reference_id)
        if row is None:
            return None
        row.status = status
        row.error_message = error_message
        await self.session.flush()
        return _to_record(row)

    async def doc_name_exists(self, collection_id: str, doc_name: str) -> bool:
        stmt = select(ReferenceORM.id).where(
            and_(
                ReferenceORM.collection_id == collection_id,
                ReferenceORM.doc_name == doc_name,
            )
        )
        return (await self.session.scalar(stmt)) is not None

    async def resolve_doc_names(
        self,
        doc_names: list[str],
        collection_ids: list[str] | None = None,
    ) -> list[ReferenceRecord]:
        if not doc_names:
            return []
        stmt = select(ReferenceORM).where(
            ReferenceORM.doc_name.in_(doc_names),
            ReferenceORM.status == IndexStatus.completed,
        )
        if collection_ids:
            stmt = stmt.where(ReferenceORM.collection_id.in_(collection_ids))
        rows = (await self.session.scalars(stmt)).all()
        return [_to_record(row) for row in rows]

    async def list_completed_ids_for_collections(
        self, collection_ids: list[str]
    ) -> list[str]:
        if not collection_ids:
            return []
        stmt = select(ReferenceORM.id).where(
            ReferenceORM.collection_id.in_(collection_ids),
            ReferenceORM.status == IndexStatus.completed,
        )
        return list(await self.session.scalars(stmt))

    async def list_completed_ids(self, reference_ids: list[str]) -> list[str]:
        if not reference_ids:
            return []
        stmt = select(ReferenceORM.id).where(
            ReferenceORM.id.in_(reference_ids),
            ReferenceORM.status == IndexStatus.completed,
        )
        return list(await self.session.scalars(stmt))

    async def set_file_path(
        self, reference_id: str, file_path: str
    ) -> ReferenceRecord | None:
        row = await self.session.get(ReferenceORM, reference_id)
        if row is None:
            return None
        row.file_path = file_path
        await self.session.flush()
        return _to_record(row)

    async def delete(self, reference_id: str) -> bool:
        """Delete a reference record by its identifier."""
        result = await self.session.execute(
            delete(ReferenceORM).where(ReferenceORM.id == reference_id),
        )
        return result.rowcount > 0


def _to_record(row: ReferenceORM) -> ReferenceRecord:
    status = (
        row.status if isinstance(row.status, IndexStatus) else IndexStatus(row.status)
    )
    return ReferenceRecord(
        id=row.id,
        collection_id=row.collection_id,
        doc_name=row.doc_name,
        filename=row.filename,
        content_type=row.content_type,
        file_path=row.file_path,
        metadata_json=row.metadata_json,
        status=status,
        error_message=row.error_message,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
