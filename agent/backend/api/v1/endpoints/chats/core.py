from collections.abc import AsyncGenerator
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy.exc import IntegrityError
from sse_starlette import ServerSentEvent
from sse_starlette.sse import EventSourceResponse

from agent.backend.api.container import ApiContainer
from agent.backend.api.exc.http import AppError
from agent.backend.api.settings import ApiSettings
from agent.backend.api.v1.deps.root import get_container, get_settings
from agent.backend.api.v1.docs.description import Descriptions
from agent.backend.api.v1.docs.examples import load_text
from agent.backend.api.v1.docs.openapi_helpers import sse_example
from agent.backend.api.v1.endpoints.chats.shared import (
    interruption_event,
    persist_completed_response,
)
from agent.backend.chatstream.core import ChatStreamService
from agent.backend.chatstream.models import StreamErrorData
from agent.backend.db.models import MessageRole
from agent.backend.services.scope import resolve_scope_reference_ids
from agent.core._agent import RunInput
from agent.core._agent.parser.core import ChatRunStatus
from agent.core.models.messages import (
    AssistantMessage,
    Message,
    Messages,
    UserMessage,
)

router = APIRouter()
log = structlog.get_logger(__name__)


def _parse_form_ids(values: list[str] | None) -> list[str]:
    if not values:
        return []
    result: list[str] = []
    for value in values:
        result.extend(v.strip() for v in value.split(",") if v.strip())
    return result


@router.post(
    "/chat",
    summary="Agentic chat (SSE)",
    description=Descriptions.CHAT_SSE,
    responses={200: {"content": sse_example(load_text("chats/chat-sse.txt"))}},
)
async def chat(
    request: Request,
    settings: Annotated[ApiSettings, Depends(get_settings)],
    container: Annotated[ApiContainer, Depends(get_container)],
    conversation_id: str = Form(...),
    message: str = Form(...),
    collection_ids: Annotated[list[str] | None, Form()] = None,
    reference_ids: Annotated[list[str] | None, Form()] = None,
    num_history_interactions: int = Form(default=5),
    top_k: int = Form(default=10),
    system_prompt: str | None = Form(default=None),
    web_search_enabled: bool = Form(default=False),
    global_query: bool = Form(default=False),
) -> EventSourceResponse:
    text = message.strip()
    if not text:
        log.warning(
            "chat_request_rejected",
            conversation_id=conversation_id,
            reason="empty_message",
        )
        raise AppError("ValidationError", "message must not be empty", 422)
    if len(text) > settings.MAX_MESSAGE_LENGTH:
        log.warning(
            "chat_request_rejected",
            conversation_id=conversation_id,
            reason="message_too_long",
            message_length=len(text),
            max_message_length=settings.MAX_MESSAGE_LENGTH,
        )
        raise AppError(
            "ValidationError",
            f"message exceeds max length {settings.MAX_MESSAGE_LENGTH}",
            422,
        )

    coll_ids = _parse_form_ids(collection_ids)
    ref_ids = _parse_form_ids(reference_ids)

    async with container.session_factory() as session:
        repos = container.repos(session)
        conversation = await repos.conversations.get(conversation_id)
        if conversation is None:
            log.warning("conversation_not_found", conversation_id=conversation_id)
            raise AppError("NotFound", f"Conversation {conversation_id} not found", 404)
        if await repos.pending_runs.get(conversation_id) is not None:
            log.warning(
                "chat_request_rejected",
                conversation_id=conversation_id,
                reason="pending_interruption",
            )
            raise AppError(
                "PendingInterruption",
                "Review or cancel the pending agent plan before sending a new message",
                409,
            )

        file_ids, _warnings = await resolve_scope_reference_ids(
            repos.references,
            collection_ids=coll_ids,
            reference_ids=ref_ids,
            message=text,
        )

        user_message = await repos.messages.create(
            conversation_id, MessageRole.user, text
        )

        past = await repos.messages.list_by_conversation(conversation_id)
        history: list[UserMessage | AssistantMessage] = []
        for msg in past[:-1]:
            if msg.role == MessageRole.user:
                history.append(UserMessage(content=msg.content))
            elif msg.role == MessageRole.assistant:
                history.append(AssistantMessage(content=msg.content))
        if num_history_interactions > 0:
            history = history[-num_history_interactions * 2 :]

        conversation_title = conversation.title
        await session.commit()

    history_messages: list[Message] = list(history)
    snapshot = RunInput(
        query=text,
        file_ids=file_ids,
        history=Messages(root=history_messages),
        memory_md_content=system_prompt or "",
        top_k=top_k,
        web_search_enabled=web_search_enabled,
        global_query=global_query,
    )

    chat_service = ChatStreamService(container.agent)
    log.info(
        "chat_stream_started",
        conversation_id=conversation_id,
        user_message_id=user_message.id,
        collection_count=len(coll_ids),
        reference_count=len(ref_ids),
        resolved_file_count=len(file_ids),
        history_message_count=len(history),
        web_search_enabled=web_search_enabled,
        global_query=global_query,
    )

    async def event_generator() -> AsyncGenerator[ServerSentEvent, None]:
        async for event in chat_service.stream(snapshot=snapshot):
            if await request.is_disconnected():
                log.info(
                    "chat_stream_disconnected",
                    conversation_id=conversation_id,
                    user_message_id=user_message.id,
                )
                return
            yield event

        if await request.is_disconnected():
            log.info(
                "chat_stream_disconnected",
                conversation_id=conversation_id,
                user_message_id=user_message.id,
            )
            return

        state = chat_service.last_state
        if state.status == ChatRunStatus.INTERRUPTED:
            if state.serialized_run_state is None or not state.interruptions:
                log.warning(
                    "chat_interruption_invalid",
                    conversation_id=conversation_id,
                    user_message_id=user_message.id,
                )
                error_payload = StreamErrorData(
                    code="InvalidInterruptionState",
                    message="The agent interrupted without resumable state",
                )
                yield ServerSentEvent(
                    event="error",
                    data=error_payload.model_dump_json(),
                )
                return
            try:
                async with container.session_factory() as session:
                    repos = container.repos(session)
                    pending = await repos.pending_runs.create(
                        conversation_id=conversation_id,
                        user_message_id=user_message.id,
                        state_json=state.serialized_run_state,
                        request_snapshot=snapshot.model_dump(mode="json"),
                        interruptions=[
                            item.model_dump(mode="json") for item in state.interruptions
                        ],
                    )
                    await session.commit()
            except IntegrityError:
                log.warning(
                    "chat_interruption_conflict",
                    conversation_id=conversation_id,
                    user_message_id=user_message.id,
                )
                error_payload = StreamErrorData(
                    code="PendingInterruptionConflict",
                    message="This conversation already has a pending agent run",
                )
                yield ServerSentEvent(
                    event="error",
                    data=error_payload.model_dump_json(),
                )
                return
            log.info(
                "chat_interrupted",
                conversation_id=conversation_id,
                user_message_id=user_message.id,
                pending_version=pending.version,
                interruption_count=len(state.interruptions),
            )
            yield interruption_event(
                conversation_id,
                pending.version,
                state.interruptions,
            )
            return
        if state.status != ChatRunStatus.COMPLETED:
            log.warning(
                "chat_stream_ended_without_completion",
                conversation_id=conversation_id,
                user_message_id=user_message.id,
                status=state.status.value,
            )
            return
        suggestion = await persist_completed_response(
            container=container,
            chat_service=chat_service,
            conversation_id=conversation_id,
            conversation_title=conversation_title,
            user_message=text,
        )
        if suggestion is not None:
            yield suggestion

    return EventSourceResponse(event_generator())
