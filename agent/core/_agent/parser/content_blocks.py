import json
from dataclasses import dataclass, field

from agent.core.models.content_blocks import (
    ContentBlock,
    ContentBlockEventType,
    ContentBlockType,
    WidgetBlockStatus,
)

from .fence_parser import FenceEvent, FenceEventType, FenceParser


@dataclass
class ContentBlockTransformer:
    fence_parser: FenceParser = field(default_factory=FenceParser)
    next_order: int = 0
    current_order: int | None = None
    current_type: ContentBlockType | None = None
    mp_chunk_snippets: dict[str, list[str]] = field(default_factory=dict)
    snippet_content: str = ""

    def transform(self, fragment: str) -> list[ContentBlock]:
        blocks: list[ContentBlock] = []
        for event in self.fence_parser.feed(fragment):
            blocks.extend(self._handle_fence_event(event))
        return blocks

    def finalize(self) -> list[ContentBlock]:
        blocks: list[ContentBlock] = []
        for event in self.fence_parser.finalize():
            blocks.extend(self._handle_fence_event(event))
        return [*blocks, *self._close_current()]

    def _handle_fence_event(self, event: FenceEvent) -> list[ContentBlock]:
        match event.type:
            case FenceEventType.PROSE_DELTA:
                return self._append_content(ContentBlockType.TEXT, event.content)
            case FenceEventType.OPEN_WIDGET:
                return [
                    *self._close_current(),
                    *self._open_block(ContentBlockType.VISUAL_WIDGET),
                ]
            case FenceEventType.WIDGET_DELTA:
                return self._append_content(
                    ContentBlockType.VISUAL_WIDGET, event.content
                )
            case FenceEventType.CLOSE_WIDGET:
                return self._close_current()
            case FenceEventType.WIDGET_ERROR:
                return [
                    *self._close_current(),
                    *self._open_block(ContentBlockType.VISUAL_WIDGET),
                    *self._close_current(status=WidgetBlockStatus.ERROR),
                ]
            case FenceEventType.OPEN_SNIPPET:
                self.snippet_content = ""
            case FenceEventType.SNIPPET_DELTA:
                self.snippet_content += event.content
            case FenceEventType.CLOSE_SNIPPET:
                self._merge_snippet_content()
                self.snippet_content = ""
        return []

    def _append_content(
        self, block_type: ContentBlockType, content: str
    ) -> list[ContentBlock]:
        if not content:
            return []
        blocks = [] if self.current_type == block_type else self._close_current()
        if self.current_type != block_type:
            blocks.extend(self._open_block(block_type))
        if self.current_order is None:
            return blocks
        blocks.append(
            ContentBlock(
                id=str(self.current_order),
                event_type=ContentBlockEventType.DELTA,
                type=block_type,
                order=self.current_order,
                status=WidgetBlockStatus.IN_PROGRESS,
                content=content,
            ),
        )
        return blocks

    def _open_block(self, block_type: ContentBlockType) -> list[ContentBlock]:
        order = self.next_order
        self.next_order += 1
        self.current_order = order
        self.current_type = block_type
        return [
            ContentBlock(
                id=str(order),
                event_type=ContentBlockEventType.OPEN,
                type=block_type,
                order=order,
                status=WidgetBlockStatus.IN_PROGRESS,
            ),
        ]

    def _close_current(
        self,
        *,
        status: WidgetBlockStatus = WidgetBlockStatus.COMPLETE,
    ) -> list[ContentBlock]:
        if self.current_order is None or self.current_type is None:
            return []
        block = ContentBlock(
            id=str(self.current_order),
            event_type=ContentBlockEventType.CLOSE,
            type=self.current_type,
            order=self.current_order,
            status=status,
        )
        self.current_order = None
        self.current_type = None
        return [block]

    def _merge_snippet_content(self) -> None:
        try:
            payload = json.loads(self.snippet_content)
        except json.JSONDecodeError:
            return
        if not isinstance(payload, list):
            return
        for item in payload:
            if not isinstance(item, dict):
                continue
            chunk_id = item.get("chunk-id")
            snippets = item.get("chunk-snippets")
            if not isinstance(chunk_id, str) or not isinstance(snippets, list):
                continue
            normalized_snippets = [
                snippet for snippet in snippets if isinstance(snippet, str) and snippet
            ]
            if chunk_id.strip() and normalized_snippets:
                self.mp_chunk_snippets.setdefault(chunk_id.strip(), []).extend(
                    normalized_snippets,
                )
