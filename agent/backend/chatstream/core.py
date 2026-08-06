import json
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field

from sse_starlette import ServerSentEvent
from agents import RawResponsesStreamEvent, RunItemStreamEvent
from agents.items import ToolCallItem

from agent.core.deps.container import Container
from agent.core.models.content_blocks import (
    ContentBlock,
    ContentBlockType,
    PersistedContentBlock,
)
from agent.core.models.messages import AssistantMessage, UserMessage
from agent.backend.chatstream.block_assembler import ContentBlockTransformer
from agent.backend.chatstream.constants import (
    ChatStreamEventNames,
    ResponseStreamEventNames,
)
from agent.backend.chatstream.models import (
    CITATION_INDEX_PATTERN,
    NameSuggestionData,
    StreamChatItem,
    StreamErrorData,
    is_untitled_conversation,
)
from agent.backend.chatstream.tool_progress import ToolProgressFormatter


@dataclass
class ChatStreamState:
    answer_text: str = ""
    completed: bool = False
    content_blocks: list[PersistedContentBlock] = field(default_factory=list)
    reasoning_text: str = ""
    validated_chunk_ids: list[str] = field(default_factory=list)
    mp_chunk_snippets: dict[str, list[str]] = field(default_factory=dict)
    had_error: bool = False


class ChatStreamService:
    def __init__(self, agent_container: Container) -> None:
        self.agent_container = agent_container
        self.last_state = ChatStreamState()

    async def stream(
        self,
        *,
        message: str,
        file_ids: list[str],
        history: list[UserMessage | AssistantMessage],
        top_k: int,
        web_search_enabled: bool,
        system_prompt: str | None = None,
        request_id: str | None = None,
    ) -> AsyncGenerator[ServerSentEvent, None]:
        state = ChatStreamState()
        transformer = ContentBlockTransformer()
        strategy = self.agent_container.agentic.get()

        reasoning_idx = 0
        content_block_events: list[ContentBlock] = []
        try:
            events = await strategy.stream_async_answer(
                query=message,
                file_ids=file_ids,
                history=history,
                top_k=top_k,
                memory_md_content=system_prompt or "",
                web_search_enabled=web_search_enabled,
            )
            async for event in events.stream_events():
                if (
                    isinstance(event, RawResponsesStreamEvent)
                    and event.data.type == ResponseStreamEventNames.TEXT_DELTA
                ):
                    content = event.data.delta
                    for content_block in transformer.transform(content):
                        content_block_events.append(content_block)
                        yield content_block.to_sse()
                    continue
                if (
                    isinstance(event, RunItemStreamEvent)
                    and event.name == ChatStreamEventNames.TOOL_CALLED
                    and isinstance(event.item, ToolCallItem)
                ):
                    progress = ToolProgressFormatter.format(event.item)
                    state.reasoning_text += progress
                    reasoning_payload = [
                        StreamChatItem(
                            idx=reasoning_idx,
                            content=progress,
                        ).model_dump()
                    ]
                    reasoning_idx += 1
                    yield ServerSentEvent(
                        event="reasoning",
                        data=json.dumps(reasoning_payload),
                    )
        except Exception as exc:
            state.had_error = True
            error_payload = StreamErrorData(
                code="InternalAIServiceError",
                message=str(exc),
            )
            yield ServerSentEvent(event="error", data=error_payload.model_dump_json())
        finally:
            state.completed = not state.had_error
            for content_block in transformer.finalize():
                content_block_events.append(content_block)
                yield content_block.to_sse()
            state.content_blocks = PersistedContentBlock.from_events(
                content_block_events,
            )
            state.mp_chunk_snippets = transformer.mp_chunk_snippets.copy()
            state.validated_chunk_ids = list(state.mp_chunk_snippets)
            state.answer_text = "".join(
                block.text or ""
                for block in state.content_blocks
                if block.type == ContentBlockType.TEXT
            )

        self.last_state = state

    @staticmethod
    def build_mapping_evidence(
        answer_text: str, validated_chunk_ids: list[str]
    ) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for match in CITATION_INDEX_PATTERN.findall(answer_text):
            idx = int(match)
            key = str(idx)
            if key in mapping:
                continue
            if 1 <= idx <= len(validated_chunk_ids):
                mapping[key] = validated_chunk_ids[idx - 1]
        if not mapping and validated_chunk_ids:
            for i, chunk_id in enumerate(validated_chunk_ids, start=1):
                mapping[str(i)] = chunk_id
        return mapping

    async def name_suggestion_event(
        self,
        conversation_title: str,
        user_message: str,
    ) -> ServerSentEvent | None:
        if not is_untitled_conversation(conversation_title):
            return None
        from agent.core.deps.models import ProgramsModel
        from agent.core.models.messages import UserMessage as UM

        program = self.agent_container.programs.get(ProgramsModel.NAME_SUGGESTION)
        result = await program.aprocess(UM(content=user_message))
        return ServerSentEvent(
            event="name-suggestion",
            data=NameSuggestionData(name=result.name).model_dump_json(),
        )
