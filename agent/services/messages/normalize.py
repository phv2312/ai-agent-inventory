"""Normalize legacy messages to content block arrays."""

from typing import Any
import uuid

from agent.db.models import MessageORM, MessageRole
from agent.models.content_blocks import (
    ContentBlock,
    ContentBlockType,
    WidgetBlockStatus,
)


def normalize_content_blocks(
    row: MessageORM,
) -> list[ContentBlock]:
    """Return ordered blocks; legacy text-only rows become one text block."""
    if row.content_blocks:
        return [ContentBlock.model_validate(b) for b in row.content_blocks]
    if row.role == MessageRole.assistant and row.content.strip():
        return [
            ContentBlock(
                id=str(uuid.uuid4()),
                type=ContentBlockType.TEXT,
                order=0,
                status=WidgetBlockStatus.COMPLETE,
                text=row.content,
            )
        ]
    return []


def blocks_to_api_dicts(blocks: list[ContentBlock]) -> list[dict[str, Any]]:
    return [b.model_dump(mode="json") for b in blocks]


def flatten_text_from_blocks(blocks: list[ContentBlock]) -> str:
    return "".join(
        b.text or ""
        for b in sorted(blocks, key=lambda x: x.order)
        if b.type == ContentBlockType.TEXT
    )
