import json
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field

from sse_starlette import ServerSentEvent

from agent.citations import mp_chunk_id_snippets_from_items
from agent.deps.container import Container
from agent.models.messages import AssistantMessage, UserMessage
from agent.models.streams import (
    CustomFunctionCall,
    ErrorEvent,
    FunctionCallArgsDoneEvent,
    FunctionCallTextDeltaEvent,
    StreamEvent,
    TextDeltaEvent,
    ThinkingDeltaEvent,
    WebSearchToolDefinition,
)
from agent.services.chatstream.models import (
    CITATION_INDEX_PATTERN,
    NameSuggestionData,
    StreamChatItem,
    StreamErrorData,
    is_untitled_conversation,
)
from agent.tools.schemas.registry import (
    InlineCitationsParameters,
    ToolNames,
    ToolSchemaRegistry,
)


@dataclass
class ChatStreamState:
    answer_text: str = ""
    reasoning_text: str = ""
    validated_chunk_ids: list[str] = field(default_factory=list)
    completed: bool = False
    had_error: bool = False


class ChatStreamService:
    def __init__(self, agent_container: Container) -> None:
        self.agent_container = agent_container
        self._last_state = ChatStreamState()

    async def stream(
        self,
        *,
        message: str,
        file_ids: list[str],
        history: list[UserMessage | AssistantMessage],
        top_k: int,
        model_name: str,
        web_search_enabled: bool,
        system_prompt: str | None = None,
    ) -> AsyncGenerator[ServerSentEvent, None]:
        state = ChatStreamState()
        strategy = self.agent_container.agentic.get()

        tool_defs = ToolSchemaRegistry.agentic_tools(
            internal_search=len(file_ids) > 0,
        )
        if web_search_enabled:
            tool_defs = [*tool_defs, WebSearchToolDefinition()]

        chat_idx = 0
        reasoning_idx = 0

        try:
            async for event in strategy.stream_async_answer(
                query=message,
                file_ids=file_ids,
                history=history,
                top_k=top_k,
                model_name=model_name,
                tools=tool_defs,
                memory_md_content=system_prompt or "",
            ):
                if isinstance(event, FunctionCallArgsDoneEvent) and isinstance(
                    event.item, CustomFunctionCall
                ):
                    if event.item.name == ToolNames.INLINE_CITATIONS_TOOL:
                        try:
                            params = InlineCitationsParameters.model_validate_json(
                                event.item.arguments
                            )
                            for chunk_id in mp_chunk_id_snippets_from_items(
                                params.citations
                            ):
                                if chunk_id not in state.validated_chunk_ids:
                                    state.validated_chunk_ids.append(chunk_id)
                        except Exception:
                            pass

                sse = self._map_event(event, chat_idx, reasoning_idx, state)
                if isinstance(event, TextDeltaEvent):
                    chat_idx += 1
                elif isinstance(
                    event, (ThinkingDeltaEvent, FunctionCallTextDeltaEvent)
                ):
                    reasoning_idx += 1
                if isinstance(event, ErrorEvent):
                    state.had_error = True
                if sse is not None:
                    yield sse

            state.completed = not state.had_error
        except Exception as exc:
            state.had_error = True
            payload = StreamErrorData(code="InternalAIServiceError", message=str(exc))
            yield ServerSentEvent(event="error", data=payload.model_dump_json())

        self._last_state = state

    @property
    def last_state(self) -> ChatStreamState:
        return self._last_state

    def _map_event(
        self,
        event: StreamEvent,
        chat_idx: int,
        reasoning_idx: int,
        state: ChatStreamState,
    ) -> ServerSentEvent | None:
        if isinstance(event, TextDeltaEvent):
            state.answer_text += event.content
            payload = [StreamChatItem(idx=chat_idx, content=event.content).model_dump()]
            return ServerSentEvent(event="chat", data=json.dumps(payload))
        if isinstance(event, ThinkingDeltaEvent):
            state.reasoning_text += event.content
            payload = [
                StreamChatItem(idx=reasoning_idx, content=event.content).model_dump()
            ]
            return ServerSentEvent(event="reasoning", data=json.dumps(payload))
        if isinstance(event, FunctionCallTextDeltaEvent):
            state.reasoning_text += event.delta
            payload = [
                StreamChatItem(idx=reasoning_idx, content=event.delta).model_dump()
            ]
            return ServerSentEvent(event="reasoning", data=json.dumps(payload))
        if isinstance(event, ErrorEvent):
            error_payload = StreamErrorData(code=event.code, message=event.message)
            return ServerSentEvent(
                event="error",
                data=error_payload.model_dump_json(),
            )
        return None

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
        from agent.deps.models import ProgramsModel
        from agent.models.messages import UserMessage as UM

        program = self.agent_container.programs.get(ProgramsModel.NAME_SUGGESTION)
        result = await program.aprocess(UM(content=user_message))
        return ServerSentEvent(
            event="name-suggestion",
            data=NameSuggestionData(name=result.name).model_dump_json(),
        )
