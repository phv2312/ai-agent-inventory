"""Assemble ordered content blocks and emit block-oriented SSE events."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sse_starlette import ServerSentEvent

from agent.models.content_blocks import (
    ContentBlock,
    ContentBlockType,
    WidgetBlockStatus,
)
from agent.models.streams import StreamEvent, TextDeltaEvent
from agent.services.chatstream.models import (
    BlockCloseData,
    BlockDeltaData,
    BlockOpenData,
)
from agent.services.visual_widget.fence_parser import (
    FenceEvent,
    FenceEventType,
    VisualizeFenceParser,
)


@dataclass
class ContentBlockAssembler:
    """Build content blocks and SSE events from agent stream events."""

    blocks: list[ContentBlock] = field(default_factory=list)
    _open_text_block_id: str | None = None
    _open_widget_block_id: str | None = None
    _fence_parser: VisualizeFenceParser = field(
        default_factory=VisualizeFenceParser,
    )
    _next_order: int = 0

    def handle(self, event: StreamEvent) -> list[ServerSentEvent]:
        if isinstance(event, TextDeltaEvent):
            return self._append_text(event.content)
        return []

    def finalize(self, *, incomplete: bool = False) -> list[ContentBlock]:
        out: list[ContentBlock] = []
        for block in self.blocks:
            finalized = block.model_copy(deep=True)
            if finalized.status == WidgetBlockStatus.STREAMING:
                if incomplete and finalized.type == ContentBlockType.VISUAL_WIDGET:
                    code = (finalized.widget_code or "").strip()
                    if not code:
                        continue
                    finalized.status = WidgetBlockStatus.INCOMPLETE
                else:
                    finalized.status = WidgetBlockStatus.COMPLETE
            if finalized.type == ContentBlockType.VISUAL_WIDGET:
                if not (finalized.widget_code or "").strip():
                    if finalized.status != WidgetBlockStatus.ERROR:
                        continue
            out.append(finalized)
        return out

    def _append_text(self, fragment: str) -> list[ServerSentEvent]:
        if not fragment:
            return []
        events: list[ServerSentEvent] = []
        for fence_event in self._fence_parser.feed(fragment):
            events.extend(self._handle_fence_event(fence_event))
        return events

    def _handle_fence_event(self, event: FenceEvent) -> list[ServerSentEvent]:
        match event.type:
            case FenceEventType.PROSE_DELTA:
                return self._append_prose(event.content)
            case FenceEventType.OPEN_WIDGET:
                return self._open_widget_block(event.module or "")
            case FenceEventType.WIDGET_DELTA:
                return self._append_widget_code(event.content)
            case FenceEventType.CLOSE_WIDGET:
                return self._close_widget_block(WidgetBlockStatus.COMPLETE)
            case FenceEventType.WIDGET_ERROR:
                return self._open_widget_error(
                    event.module or "unknown",
                    event.error_message or "Invalid visualize fence",
                )
        return []

    def _append_prose(self, fragment: str) -> list[ServerSentEvent]:
        if not fragment:
            return []
        events: list[ServerSentEvent] = []
        if self._open_text_block_id is None:
            events.extend(self._open_text_block())
        block = self._block_by_id(self._open_text_block_id)
        if block is None:
            return events
        block.text = (block.text or "") + fragment
        events.append(self._delta_event(block.id, fragment))
        return events

    def _append_widget_code(self, fragment: str) -> list[ServerSentEvent]:
        if not fragment:
            return []
        block = self._block_by_id(self._open_widget_block_id)
        if block is None:
            return []
        block.widget_code = (block.widget_code or "") + fragment
        return [self._delta_event(block.id, fragment)]

    def _open_widget_block(self, module: str) -> list[ServerSentEvent]:
        events: list[ServerSentEvent] = []
        if self._open_text_block_id is not None:
            events.extend(self._close_text_block())
        block_id = str(uuid.uuid4())
        block = ContentBlock(
            id=block_id,
            type=ContentBlockType.VISUAL_WIDGET,
            order=self._next_order,
            status=WidgetBlockStatus.STREAMING,
            module=module,
            title=None,
            loading_messages=[],
            widget_code="",
        )
        self._next_order += 1
        self.blocks.append(block)
        self._open_widget_block_id = block_id
        events.append(self._open_event(block))
        return events

    def _open_widget_error(self, module: str, message: str) -> list[ServerSentEvent]:
        events: list[ServerSentEvent] = []
        if self._open_text_block_id is not None:
            events.extend(self._close_text_block())
        block_id = str(uuid.uuid4())
        block = ContentBlock(
            id=block_id,
            type=ContentBlockType.VISUAL_WIDGET,
            order=self._next_order,
            status=WidgetBlockStatus.ERROR,
            title=None,
            loading_messages=[],
            widget_code="",
            error_message=message,
        )
        self._next_order += 1
        self.blocks.append(block)
        events.append(self._open_event(block))
        events.append(
            self._close_event(block_id, WidgetBlockStatus.ERROR, error_message=message),
        )
        return events

    def _close_widget_block(self, status: WidgetBlockStatus) -> list[ServerSentEvent]:
        if self._open_widget_block_id is None:
            return []
        block_id = self._open_widget_block_id
        block = self._block_by_id(block_id)
        self._open_widget_block_id = None
        if block is None:
            return []
        block.status = status
        events = [self._close_event(block_id, status)]
        events.extend(self._open_text_block())
        return events

    def _open_text_block(self) -> list[ServerSentEvent]:
        block_id = str(uuid.uuid4())
        block = ContentBlock(
            id=block_id,
            type=ContentBlockType.TEXT,
            order=self._next_order,
            status=WidgetBlockStatus.STREAMING,
            text="",
        )
        self._next_order += 1
        self.blocks.append(block)
        self._open_text_block_id = block_id
        return [self._open_event(block)]

    def _close_text_block(self) -> list[ServerSentEvent]:
        if self._open_text_block_id is None:
            return []
        block_id = self._open_text_block_id
        block = self._block_by_id(block_id)
        self._open_text_block_id = None
        if block is None:
            return []
        block.status = WidgetBlockStatus.COMPLETE
        return [self._close_event(block_id, WidgetBlockStatus.COMPLETE)]

    def _block_by_id(self, block_id: str | None) -> ContentBlock | None:
        if block_id is None:
            return None
        for block in self.blocks:
            if block.id == block_id:
                return block
        return None

    def _open_event(self, block: ContentBlock) -> ServerSentEvent:
        payload = BlockOpenData(
            block_id=block.id,
            type=block.type.value,
            order=block.order,
            module=block.module,
            title=block.title,
            loading_messages=block.loading_messages,
        )
        return ServerSentEvent(
            event="block-open",
            data=payload.model_dump_json(),
        )

    def _delta_event(self, block_id: str, content: str) -> ServerSentEvent:
        payload = BlockDeltaData(block_id=block_id, content=content)
        return ServerSentEvent(
            event="block-delta",
            data=payload.model_dump_json(),
        )

    def _close_event(
        self,
        block_id: str,
        status: WidgetBlockStatus,
        *,
        error_message: str | None = None,
    ) -> ServerSentEvent:
        payload = BlockCloseData(
            block_id=block_id,
            status=status.value,
            error_message=error_message,
        )
        return ServerSentEvent(
            event="block-close",
            data=payload.model_dump_json(),
        )

    def close_open_blocks_incomplete(self) -> list[ServerSentEvent]:
        """Emit block-close for streaming blocks when stream aborts."""
        events: list[ServerSentEvent] = []
        for fence_event in self._fence_parser.flush_partial_prose():
            events.extend(self._handle_fence_event(fence_event))
        if self._open_widget_block_id is not None:
            block_id = self._open_widget_block_id
            block = self._block_by_id(block_id)
            self._open_widget_block_id = None
            if block is not None:
                code = (block.widget_code or "").strip()
                if not code:
                    self.blocks = [b for b in self.blocks if b.id != block_id]
                else:
                    block.status = WidgetBlockStatus.INCOMPLETE
                    events.append(
                        self._close_event(block_id, WidgetBlockStatus.INCOMPLETE),
                    )
        if self._open_text_block_id is not None:
            block_id = self._open_text_block_id
            block = self._block_by_id(block_id)
            self._open_text_block_id = None
            if block is not None:
                block.status = WidgetBlockStatus.COMPLETE
                events.append(self._close_event(block_id, WidgetBlockStatus.COMPLETE))
        return events
