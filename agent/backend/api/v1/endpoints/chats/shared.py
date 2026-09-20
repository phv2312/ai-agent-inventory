import json

import structlog
from sse_starlette import ServerSentEvent

from agent.backend.api.container import ApiContainer
from agent.backend.chatstream.core import ChatStreamService
from agent.backend.chatstream.models import (
    InterruptionEventData,
    NameSuggestionData,
    is_untitled_conversation,
)
from agent.backend.db.models import MessageRole
from agent.core.tools import AgentInterruption

log = structlog.get_logger(__name__)


def interruption_event(
    conversation_id: str,
    version: int,
    interruptions: list[AgentInterruption],
) -> ServerSentEvent:
    data = InterruptionEventData(
        conversation_id=conversation_id,
        version=version,
        interruptions=interruptions,
    )
    return ServerSentEvent(event="interruption", data=data.model_dump_json())


async def persist_completed_response(
    *,
    container: ApiContainer,
    chat_service: ChatStreamService,
    conversation_id: str,
    conversation_title: str,
    user_message: str,
    pending_version: int | None = None,
) -> ServerSentEvent | None:
    state = chat_service.last_state
    has_output = bool(state.answer_text.strip()) or bool(state.content_blocks)
    async with container.session_factory() as session:
        repos = container.repos(session)
        suggestion: ServerSentEvent | None = None
        if has_output:
            content = state.answer_text
            mapping = ChatStreamService.build_mapping_evidence(
                content,
                state.validated_chunk_ids,
            )
            content_blocks = [
                block.model_dump(mode="json") for block in state.content_blocks
            ] or None
            msg = await repos.messages.create(
                conversation_id,
                MessageRole.assistant,
                content,
                mapping_evidence=mapping or None,
                content_blocks=content_blocks,
            )
            if state.mp_chunk_snippets:
                await repos.citations.bulk_create(msg.id, state.mp_chunk_snippets)

            suggestion = await chat_service.name_suggestion_event(
                conversation_title,
                user_message,
            )
            if (
                suggestion is not None
                and is_untitled_conversation(conversation_title)
                and suggestion.data is not None
            ):
                data = json.loads(suggestion.data)
                name = NameSuggestionData.model_validate(data).name
                await repos.conversations.update_title(conversation_id, name)
        if pending_version is not None:
            deleted = await repos.pending_runs.delete(
                conversation_id,
                pending_version,
            )
            if not deleted:
                log.warning(
                    "pending_run_completion_conflict",
                    conversation_id=conversation_id,
                    pending_version=pending_version,
                )
                raise RuntimeError("The pending run changed before completion")
        await session.commit()
        log.info(
            "chat_response_persisted",
            conversation_id=conversation_id,
            has_output=has_output,
            citation_count=len(state.mp_chunk_snippets),
            pending_version=pending_version,
            name_suggested=suggestion is not None,
        )
        return suggestion
