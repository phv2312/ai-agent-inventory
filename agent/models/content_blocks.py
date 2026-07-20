from dataclasses import asdict, dataclass
from enum import StrEnum
import json

from sse_starlette import ServerSentEvent
from pydantic import BaseModel


class ContentBlockType(StrEnum):
    TEXT = "text"
    VISUAL_WIDGET = "visual_widget"


class WidgetBlockStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    ERROR = "error"


class ContentBlockEventType(StrEnum):
    OPEN = "block-open"
    DELTA = "block-delta"
    CLOSE = "block-close"


@dataclass
class ContentBlock:
    id: str
    event_type: ContentBlockEventType
    type: ContentBlockType
    order: int
    status: WidgetBlockStatus
    content: str | None = None
    error_message: str | None = None

    def to_sse(self) -> ServerSentEvent:
        return ServerSentEvent(
            event=self.event_type.value,
            data=json.dumps(asdict(self)),
        )


class PersistedContentBlock(BaseModel):
    id: str
    type: ContentBlockType
    order: int
    status: WidgetBlockStatus
    text: str | None = None
    widget_code: str | None = None
    error_message: str | None = None

    @classmethod
    def from_events(
        cls,
        events: list[ContentBlock],
    ) -> list["PersistedContentBlock"]:
        blocks: dict[int, PersistedContentBlock] = {}
        chunks: dict[int, list[str]] = {}
        for event in events:
            if event.event_type == ContentBlockEventType.OPEN:
                blocks[event.order] = cls(
                    id=event.id,
                    type=event.type,
                    order=event.order,
                    status=event.status,
                    error_message=event.error_message,
                )
                chunks[event.order] = []
                continue
            if event.event_type == ContentBlockEventType.DELTA:
                chunks.setdefault(event.order, []).append(event.content or "")
                continue
            block = blocks.get(event.order)
            if block is not None:
                blocks[event.order] = block.model_copy(
                    update={
                        "status": event.status,
                        "error_message": event.error_message,
                    },
                )

        result: list[PersistedContentBlock] = []
        for order, block in sorted(blocks.items()):
            content = "".join(chunks[order])
            update = (
                {"text": content}
                if block.type == ContentBlockType.TEXT
                else {"widget_code": content}
            )
            result.append(block.model_copy(update=update))
        return result
