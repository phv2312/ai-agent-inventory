import json
from dataclasses import dataclass, field

from sse_starlette import ServerSentEvent

from agent.models.content_blocks import (
    ContentBlock,
    ContentBlockEventType,
    ContentBlockType,
    WidgetBlockStatus,
)
from agent.models.streams import StreamEvent, TextDeltaEvent
from agent.services.visual_widget.fence_parser import (
    FenceEvent,
    FenceEventType,
    FenceParser,
)


@dataclass
class ContentBlockTransformer:
    fence_parser: FenceParser = field(default_factory=FenceParser)
    next_order: int = 0
    current_order: int | None = None
    current_type: ContentBlockType | None = None
    current_event: ContentBlockEventType | None = None
    snippet_content: str = ""
    mp_chunk_snippets: dict[str, list[str]] = field(default_factory=dict)

    def transform(self, fragment: str) -> list[ContentBlock]:
        blocks: list[ContentBlock] = []
        for event in self.fence_parser.feed(fragment):
            blocks.extend(self.handle_fence_event(event))
        return blocks

    def flush(self) -> list[ContentBlock]:
        blocks: list[ContentBlock] = []
        for event in self.fence_parser.finalize():
            blocks.extend(self.handle_fence_event(event))
        return blocks

    def finalize(self) -> list[ContentBlock]:
        blocks = self.flush()
        match self.current_event:
            case ContentBlockEventType.OPEN | ContentBlockEventType.DELTA:
                blocks.extend(self.close_current())
            case _:
                pass
        return blocks

    def handle_fence_event(self, event: FenceEvent) -> list[ContentBlock]:
        self.update_fence_status(event.type)
        match event.type:
            case FenceEventType.PROSE_DELTA:
                return self.append_content(ContentBlockType.TEXT, event.content)
            case FenceEventType.OPEN_WIDGET:
                return self.open_widget(event.module or "")
            case FenceEventType.WIDGET_DELTA:
                return self.append_content(
                    ContentBlockType.VISUAL_WIDGET, event.content
                )
            case FenceEventType.CLOSE_WIDGET:
                return self.close_current()
            case FenceEventType.WIDGET_ERROR:
                return self.open_widget_error(
                    event.module or "unknown",
                    event.error_message or "Invalid visualize fence",
                )
            case FenceEventType.OPEN_SNIPPET:
                self.snippet_content = ""
            case FenceEventType.SNIPPET_DELTA:
                self.snippet_content += event.content
            case FenceEventType.CLOSE_SNIPPET:
                self.merge_snippet_content()
                self.snippet_content = ""
        return []

    def merge_snippet_content(self) -> None:
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
            normalized_chunk_id = chunk_id.strip()
            normalized_snippets = [
                snippet for snippet in snippets if isinstance(snippet, str) and snippet
            ]
            if normalized_chunk_id and normalized_snippets:
                self.mp_chunk_snippets.setdefault(normalized_chunk_id, []).extend(
                    normalized_snippets,
                )

    def update_fence_status(self, event_type: FenceEventType) -> None:
        mp_event_status: dict[FenceEventType, ContentBlockEventType] = {
            FenceEventType.PROSE_DELTA: ContentBlockEventType.DELTA,
            FenceEventType.OPEN_WIDGET: ContentBlockEventType.OPEN,
            FenceEventType.WIDGET_DELTA: ContentBlockEventType.DELTA,
            FenceEventType.CLOSE_WIDGET: ContentBlockEventType.CLOSE,
        }

        self.current_event = mp_event_status.get(event_type, self.current_event)

        return None

    def append_content(
        self,
        block_type: ContentBlockType,
        content: str,
    ) -> list[ContentBlock]:
        if not content:
            return []
        blocks = self.close_current() if self.current_type != block_type else []
        if self.current_type != block_type:
            blocks.extend(self.open_block(block_type))
        if self.current_order is None:
            return blocks
        match block_type:
            case ContentBlockType.TEXT:
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
            case ContentBlockType.VISUAL_WIDGET:
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

    def open_widget(self, module: str) -> list[ContentBlock]:
        blocks = self.close_current()
        blocks.extend(self.open_block(ContentBlockType.VISUAL_WIDGET))
        return blocks

    def open_widget_error(self, module: str, error_message: str) -> list[ContentBlock]:
        blocks = self.close_current()
        blocks.extend(self.open_block(ContentBlockType.VISUAL_WIDGET))
        blocks.extend(self.close_current(status=WidgetBlockStatus.ERROR))
        return blocks

    def open_block(
        self,
        block_type: ContentBlockType,
    ) -> list[ContentBlock]:
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

    def close_current(
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


@dataclass
class ContentBlockAssembler:
    transformer: ContentBlockTransformer = field(
        default_factory=lambda: ContentBlockTransformer(FenceParser()),
    )

    def handle(self, event: StreamEvent) -> list[ServerSentEvent]:
        if not isinstance(event, TextDeltaEvent):
            return []
        return self.emit(self.transformer.transform(event.content))

    def close_open_blocks(self) -> list[ServerSentEvent]:
        return self.close_open_blocks_with_status(WidgetBlockStatus.COMPLETE)

    def close_open_blocks_incomplete(self) -> list[ServerSentEvent]:
        return self.close_open_blocks_with_status(WidgetBlockStatus.ERROR)

    def close_open_blocks_with_status(
        self,
        status: WidgetBlockStatus,
    ) -> list[ServerSentEvent]:
        blocks = self.transformer.flush()
        if self.transformer.current_type == ContentBlockType.TEXT:
            status = WidgetBlockStatus.COMPLETE
        blocks.extend(self.transformer.close_current(status=status))
        return self.emit(blocks)

    def emit(self, blocks: list[ContentBlock]) -> list[ServerSentEvent]:
        return [block.to_sse() for block in blocks]
