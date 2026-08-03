from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from agent.backend.db.models import IndexStatus, MessageRole


@dataclass
class ConversationRecord:
    id: str
    title: str
    created_at: datetime
    updated_at: datetime


@dataclass
class MessageRecord:
    id: str
    conversation_id: str
    role: MessageRole
    content: str
    mapping_evidence: dict[str, str] | None
    content_blocks: list[dict[str, Any]] | None
    created_at: datetime


@dataclass
class CitationRecord:
    id: str
    message_id: str
    chunk_id: str
    snippets: list[str]
    created_at: datetime


@dataclass
class CollectionRecord:
    id: str
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


@dataclass
class ReferenceRecord:
    id: str
    collection_id: str
    doc_name: str
    filename: str
    content_type: str
    file_path: str
    metadata_json: dict[str, object] | None
    status: IndexStatus
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class ConversationRepository(Protocol):
    async def create(self, title: str = "") -> ConversationRecord: ...
    async def get(self, conversation_id: str) -> ConversationRecord | None: ...
    async def list(
        self, skip: int = 0, limit: int = 20
    ) -> list[ConversationRecord]: ...
    async def update_title(
        self, conversation_id: str, title: str
    ) -> ConversationRecord | None: ...
    async def delete(self, conversation_id: str) -> bool: ...


class MessageRepository(Protocol):
    async def create(
        self,
        conversation_id: str,
        role: MessageRole,
        content: str,
        mapping_evidence: dict[str, str] | None = None,
        content_blocks: list[dict[str, Any]] | None = None,
    ) -> MessageRecord: ...
    async def list_by_conversation(
        self, conversation_id: str
    ) -> list[MessageRecord]: ...
    async def count_by_conversation(self, conversation_id: str) -> int: ...


class CitationRepository(Protocol):
    async def bulk_create(
        self,
        message_id: str,
        mp_chunk_snippets: dict[str, list[str]],
    ) -> list[CitationRecord]: ...
    async def get_snippets(
        self, message_id: str, chunk_id: str
    ) -> list[str] | None: ...
    async def snippets_for_chunks(
        self, message_id: str, chunk_ids: list[str]
    ) -> dict[str, list[str]]: ...
    async def list_by_message(self, message_id: str) -> list[CitationRecord]: ...


class CollectionRepository(Protocol):
    async def create(
        self, name: str, description: str | None = None
    ) -> CollectionRecord: ...
    async def get(self, collection_id: str) -> CollectionRecord | None: ...
    async def list(self, skip: int = 0, limit: int = 20) -> list[CollectionRecord]: ...
    async def update(
        self,
        collection_id: str,
        name: str | None = None,
        description: str | None = None,
    ) -> CollectionRecord | None: ...
    async def delete(self, collection_id: str) -> bool: ...


class ReferenceRepository(Protocol):
    async def create(
        self,
        collection_id: str,
        doc_name: str,
        filename: str,
        content_type: str,
        file_path: str,
        metadata_json: dict[str, object] | None = None,
    ) -> ReferenceRecord: ...
    async def get(self, reference_id: str) -> ReferenceRecord | None: ...
    async def list_by_collection(self, collection_id: str) -> list[ReferenceRecord]: ...
    async def update_status(
        self,
        reference_id: str,
        status: IndexStatus,
        error_message: str | None = None,
    ) -> ReferenceRecord | None: ...
    async def doc_name_exists(self, collection_id: str, doc_name: str) -> bool: ...
    async def resolve_doc_names(
        self,
        doc_names: list[str],
        collection_ids: list[str] | None = None,
    ) -> list[ReferenceRecord]: ...
    async def list_completed_ids_for_collections(
        self, collection_ids: list[str]
    ) -> list[str]: ...
    async def list_completed_ids(self, reference_ids: list[str]) -> list[str]: ...
    async def set_file_path(
        self, reference_id: str, file_path: str
    ) -> ReferenceRecord | None: ...
    async def delete(self, reference_id: str) -> bool: ...
