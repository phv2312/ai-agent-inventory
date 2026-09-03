from functools import wraps
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Concatenate

from agents import (
    RawResponsesStreamEvent,
    RunItemStreamEvent,
    RunResultStreaming,
)
from agents.items import ToolCallItem
from openai.types.responses import ResponseTextDeltaEvent

from agent.core.models.content_blocks import (
    ContentBlock,
    ContentBlockType,
    PersistedContentBlock as PContentBlock,
)
from agent.core.tools import AgentInterruption

from .content_blocks import ContentBlockTransformer


class ChatRunStatus(StrEnum):
    RUNNING = "running"
    INTERRUPTED = "interrupted"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ParsedStreamError:
    exception: str


@dataclass
class ToolProgressDelta:
    idx: int = field(default=0)
    content: str = field(default="")


@dataclass
class ChatStreamState:
    answer_text: str = ""
    completed: bool = False
    content_blocks: list[PContentBlock] = field(default_factory=list)
    reasoning_text: str = ""
    validated_chunk_ids: list[str] = field(default_factory=list)
    mp_chunk_snippets: dict[str, list[str]] = field(default_factory=dict)
    had_error: bool = False
    status: ChatRunStatus = ChatRunStatus.RUNNING
    serialized_run_state: str | None = None
    interruptions: list[AgentInterruption] = field(default_factory=list)


type ParsedStreamEvent = ContentBlock | ParsedStreamError | ToolProgressDelta


type FuncT[**P] = Callable[
    Concatenate["StreamParser", RunResultStreaming, P],
    AsyncGenerator[ParsedStreamEvent, None],
]


@dataclass
class RunstateRepository:
    result: RunResultStreaming
    state: ChatStreamState = field(default_factory=ChatStreamState)
    content_blocks: list[ContentBlock] = field(default_factory=list)
    transformer: ContentBlockTransformer = field(
        default_factory=ContentBlockTransformer
    )

    def close_stream_result(self) -> None:
        if self.result.run_loop_exception is not None:
            raise self.result.run_loop_exception
        if self.result.interruptions:
            self.state.status = ChatRunStatus.INTERRUPTED
            self.state.serialized_run_state = self.result.to_state().to_string()
            self.state.interruptions = [
                AgentInterruption.from_approval_item(item)
                for item in self.result.interruptions
            ]
        else:
            self.state.status = ChatRunStatus.COMPLETED

    async def finalize_parsing(self) -> AsyncGenerator[ContentBlock, None]:
        self.state.completed = self.state.status == ChatRunStatus.COMPLETED
        for content_block in self.transformer.finalize():
            self.content_blocks.append(content_block)
            yield content_block
        self.state.content_blocks = PContentBlock.from_events(self.content_blocks)
        self.state.mp_chunk_snippets = self.transformer.mp_chunk_snippets.copy()
        self.state.validated_chunk_ids = list(self.state.mp_chunk_snippets)
        self.state.answer_text = "".join(
            block.text or ""
            for block in self.state.content_blocks
            if block.type == ContentBlockType.TEXT
        )

    def catch_exc(self) -> None:
        self.state.had_error = True
        self.state.status = ChatRunStatus.FAILED


def auto_catch_exceptions[**P](
    func: FuncT[P],
) -> FuncT[P]:
    @wraps(func)
    async def wrapper(
        self: "StreamParser",
        result: RunResultStreaming,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> AsyncGenerator[ParsedStreamEvent, None]:
        runstate_repo = RunstateRepository(result=result)
        try:
            kwargs["transformer"] = runstate_repo.transformer
            async for item in func(self, result, *args, **kwargs):
                if isinstance(item, ContentBlock):
                    runstate_repo.content_blocks.append(item)
                yield item
            runstate_repo.close_stream_result()
        except Exception as exc:
            runstate_repo.catch_exc()
            yield ParsedStreamError(exception=str(exc))

        finally:
            async for item in runstate_repo.finalize_parsing():
                yield item
            self.last_state = runstate_repo.state

    return wrapper


class StreamParser:
    def __init__(self) -> None:
        self.last_state = ChatStreamState()

    @auto_catch_exceptions
    async def parse(
        self,
        result: RunResultStreaming,
        *,
        transformer: ContentBlockTransformer | None = None,
    ) -> AsyncGenerator[ParsedStreamEvent, None]:
        def _format_tool_progress(item: ToolCallItem) -> str:
            return f"Using {item.name or 'tool'}..."

        transformer = transformer or ContentBlockTransformer()
        reasoning_idx = 0
        async for event in result.stream_events():
            if (
                isinstance(event, RawResponsesStreamEvent)
                and isinstance(event.data, ResponseTextDeltaEvent)
                and event.data.type == "response.output_text.delta"
            ):
                for content_block in transformer.transform(event.data.delta):
                    yield content_block
                continue
            if (
                isinstance(event, RunItemStreamEvent)
                and event.name == "tool_called"
                and isinstance(event.item, ToolCallItem)
            ):
                yield ToolProgressDelta(
                    idx=reasoning_idx,
                    content=_format_tool_progress(event.item),
                )
                reasoning_idx += 1
