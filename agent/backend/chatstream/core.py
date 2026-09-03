import json
from collections.abc import AsyncGenerator

from agents import RunResultStreaming
from sse_starlette import ServerSentEvent

from agent.backend.chatstream.models import (
    CITATION_INDEX_PATTERN,
    NameSuggestionData,
    StreamChatItem,
    StreamErrorData,
    is_untitled_conversation,
)
from agent.core.deps.container import Container
from agent.core._agent import RunInput
from agent.core._agent.parser import (
    ChatRunStatus,
    ChatStreamState,
    ParsedStreamError,
    StreamParser,
    ToolProgressDelta,
)
from agent.core.models.content_blocks import ContentBlock
from agent.core.models.messages import AssistantMessage, Message, Messages, UserMessage


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
        global_query: bool = False,
        system_prompt: str | None = None,
    ) -> AsyncGenerator[ServerSentEvent, None]:
        orchestrator = self.agent_container.agent.get()
        try:
            history_messages: list[Message] = list(history)
            snapshot = RunInput(
                query=message,
                file_ids=file_ids,
                history=Messages(root=history_messages),
                top_k=top_k,
                memory_md_content=system_prompt or "",
                web_search_enabled=web_search_enabled,
                global_query=global_query,
            )
            result = await orchestrator.stream(snapshot)
            async for event in self._parse_result(result):
                yield event
        except Exception as exc:
            async for event in self._stream_setup_error(exc):
                yield event

    async def resume(
        self,
        *,
        snapshot: RunInput,
        state_json: str,
        decision: str,
        feedback: str = "",
    ) -> AsyncGenerator[ServerSentEvent, None]:
        orchestrator = self.agent_container.agent.get()
        try:
            agent, run_state = await orchestrator.load_run_state(snapshot, state_json)
            interruptions = run_state.get_interruptions()
            if not interruptions:
                raise ValueError("The saved run has no pending interruptions")
            if decision == "approve":
                for interruption in interruptions:
                    run_state.approve(interruption)
            elif decision == "revise":
                rejection_message = (
                    "The human reviewer requested these plan changes:\n"
                    f"{feedback}\n\n"
                    "Revise the plan and submit the complete replacement plan for "
                    "approval. Do not execute the plan or write the final answer."
                )
                for interruption in interruptions:
                    run_state.reject(
                        interruption,
                        rejection_message=rejection_message,
                    )
            else:
                raise ValueError(f"Unsupported interruption decision: {decision}")

            result = orchestrator.resume(agent, run_state)
            async for event in self._parse_result(result):
                yield event
        except Exception as exc:
            async for event in self._stream_setup_error(exc):
                yield event

    async def _parse_result(
        self,
        result: RunResultStreaming,
    ) -> AsyncGenerator[ServerSentEvent, None]:
        parser = StreamParser()
        reasoning_text = ""
        async for event in parser.parse(result):
            if isinstance(event, ContentBlock):
                yield event.to_sse()
                continue
            if isinstance(event, ToolProgressDelta):
                reasoning_text += event.content
                payload = [
                    StreamChatItem(
                        idx=event.idx,
                        content=event.content,
                    ).model_dump(),
                ]
                yield ServerSentEvent(event="reasoning", data=json.dumps(payload))
                continue
            if isinstance(event, ParsedStreamError):
                error_payload = StreamErrorData(
                    code="InternalAIServiceError",
                    message=event.exception,
                )
                yield ServerSentEvent(
                    event="error",
                    data=error_payload.model_dump_json(),
                )
        self.last_state = parser.last_state
        self.last_state.reasoning_text = reasoning_text

    async def _stream_setup_error(
        self,
        exc: Exception,
    ) -> AsyncGenerator[ServerSentEvent, None]:
        self.last_state = ChatStreamState(
            had_error=True,
            status=ChatRunStatus.FAILED,
        )
        error_payload = StreamErrorData(
            code="InternalAIServiceError",
            message=str(exc),
        )
        yield ServerSentEvent(event="error", data=error_payload.model_dump_json())

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
