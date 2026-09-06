import json
from collections.abc import AsyncGenerator
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy.exc import IntegrityError
from sse_starlette import ServerSentEvent
from sse_starlette.sse import EventSourceResponse

from agent.backend.api.container import ApiContainer
from agent.backend.api.exc.http import AppError
from agent.backend.api.v1.deps.root import get_container, get_settings
from agent.backend.api.settings import ApiSettings
from agent.backend.db.models import MessageRole
from agent.backend.chatstream.core import ChatStreamService
from agent.backend.chatstream.models import (
    InterruptionEventData,
    NameSuggestionData,
    StreamErrorData,
    is_untitled_conversation,
)
from agent.backend.api.v1.docs.description import Descriptions
from agent.backend.api.v1.docs.examples import load_text
from agent.backend.api.v1.docs.openapi_helpers import sse_example
from agent.backend.api.v1.payload.chats import (
    InterruptionDecision,
    InterruptionDecisionRequest,
    LinkPreviewItemResponse,
    LinkPreviewRequest,
    LinkPreviewResponse,
)
from agent.backend.services.link_preview import LinkPreviewService
from agent.backend.services.scope import resolve_scope_reference_ids
from agent.core.models.messages import (
    AssistantMessage,
    Message,
    Messages,
    UserMessage,
)
from agent.core._agent import RunInput
from agent.core._agent.parser.core import ChatRunStatus
from agent.core.tools import AgentInterruption

router = APIRouter()
_link_preview_service = LinkPreviewService()


def _interruption_event(
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


async def _persist_completed_response(
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
                raise RuntimeError("The pending run changed before completion")
        await session.commit()
        return suggestion


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
        raise AppError("ValidationError", "message must not be empty", 422)
    if len(text) > settings.MAX_MESSAGE_LENGTH:
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
            raise AppError("NotFound", f"Conversation {conversation_id} not found", 404)
        if await repos.pending_runs.get(conversation_id) is not None:
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

    async def event_generator() -> AsyncGenerator[ServerSentEvent, None]:
        async for event in chat_service.stream(
            message=text,
            file_ids=file_ids,
            history=history,
            top_k=top_k,
            web_search_enabled=web_search_enabled,
            global_query=global_query,
            system_prompt=system_prompt,
        ):
            if await request.is_disconnected():
                return
            yield event

        if await request.is_disconnected():
            return

        state = chat_service.last_state
        if state.status == ChatRunStatus.INTERRUPTED:
            if state.serialized_run_state is None or not state.interruptions:
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
                error_payload = StreamErrorData(
                    code="PendingInterruptionConflict",
                    message="This conversation already has a pending agent run",
                )
                yield ServerSentEvent(
                    event="error",
                    data=error_payload.model_dump_json(),
                )
                return
            yield _interruption_event(
                conversation_id,
                pending.version,
                state.interruptions,
            )
            return
        if state.status != ChatRunStatus.COMPLETED:
            return
        suggestion = await _persist_completed_response(
            container=container,
            chat_service=chat_service,
            conversation_id=conversation_id,
            conversation_title=conversation_title,
            user_message=text,
        )
        if suggestion is not None:
            yield suggestion

    return EventSourceResponse(event_generator())


@router.get(
    "/{conversation_id}/interruptions",
    summary="Get the pending agent interruption",
    response_model=InterruptionEventData,
)
async def get_pending_interruption(
    conversation_id: str,
    container: Annotated[ApiContainer, Depends(get_container)],
) -> InterruptionEventData:
    async with container.session_factory() as session:
        repos = container.repos(session)
        if await repos.conversations.get(conversation_id) is None:
            raise AppError("NotFound", f"Conversation {conversation_id} not found", 404)
        pending = await repos.pending_runs.get(conversation_id)
    if pending is None:
        raise AppError("NotFound", "There is no agent plan awaiting review", 404)
    return InterruptionEventData.model_validate(
        {
            "conversation_id": conversation_id,
            "version": pending.version,
            "interruptions": pending.interruptions,
        }
    )


@router.post(
    "/{conversation_id}/interruptions",
    summary="Respond to the pending agent interruption (SSE)",
)
@router.post(
    "/{conversation_id}/interruptions/resume",
    summary="Resume a pending agent interruption (SSE)",
)
async def respond_to_interruption(
    request: Request,
    conversation_id: str,
    payload: InterruptionDecisionRequest,
    container: Annotated[ApiContainer, Depends(get_container)],
) -> EventSourceResponse:
    async with container.session_factory() as session:
        repos = container.repos(session)
        conversation = await repos.conversations.get(conversation_id)
        if conversation is None:
            raise AppError("NotFound", f"Conversation {conversation_id} not found", 404)
        pending = await repos.pending_runs.get(conversation_id)
        if pending is None:
            raise AppError("NotFound", "There is no agent plan awaiting review", 404)
        expected_ids = {item["id"] for item in pending.interruptions}
        if (
            pending.version != payload.version
            or set(payload.interruption_ids) != expected_ids
        ):
            raise AppError(
                "StaleInterruption",
                "The pending interruption changed; reload it before responding",
                409,
            )

        if payload.decision == InterruptionDecision.CANCEL:
            deleted = await repos.pending_runs.delete(
                conversation_id,
                payload.version,
            )
            if not deleted:
                raise AppError(
                    "InterruptionConflict",
                    "The pending interruption is already being handled",
                    409,
                )
            await session.commit()

    if payload.decision == InterruptionDecision.CANCEL:

        async def cancelled_events() -> AsyncGenerator[ServerSentEvent, None]:
            yield ServerSentEvent(
                event="interruption-resolved",
                data=json.dumps(
                    {
                        "conversation_id": conversation_id,
                        "version": payload.version,
                        "status": "cancelled",
                    }
                ),
            )

        return EventSourceResponse(cancelled_events())

    snapshot = RunInput.model_validate(pending.request_snapshot)
    chat_service = ChatStreamService(container.agent)
    resume_decision: Literal["approve", "revise"] = "approve"
    if payload.decision == InterruptionDecision.REVISE:
        resume_decision = "revise"

    async def resumed_events() -> AsyncGenerator[ServerSentEvent, None]:
        async for event in chat_service.resume(
            snapshot=snapshot,
            state_json=pending.state_json,
            decision=resume_decision,
            feedback=payload.feedback or "",
        ):
            if await request.is_disconnected():
                return
            yield event

        state = chat_service.last_state
        if state.status not in {
            ChatRunStatus.INTERRUPTED,
            ChatRunStatus.COMPLETED,
        }:
            return

        if state.status == ChatRunStatus.INTERRUPTED:
            if state.serialized_run_state is None or not state.interruptions:
                return
            async with container.session_factory() as session:
                repos = container.repos(session)
                revised = await repos.pending_runs.replace(
                    conversation_id=conversation_id,
                    version=payload.version,
                    state_json=state.serialized_run_state,
                    interruptions=[
                        item.model_dump(mode="json") for item in state.interruptions
                    ],
                )
                await session.commit()
            if revised is None:
                return
            yield _interruption_event(
                conversation_id,
                revised.version,
                state.interruptions,
            )
            return

        suggestion = await _persist_completed_response(
            container=container,
            chat_service=chat_service,
            conversation_id=conversation_id,
            conversation_title=conversation.title,
            user_message=snapshot.query,
            pending_version=payload.version,
        )
        if suggestion is not None:
            yield suggestion

    return EventSourceResponse(resumed_events())


@router.post(
    "/link-previews",
    summary="Fetch link preview metadata",
    response_model=LinkPreviewResponse,
)
async def get_link_previews(
    payload: LinkPreviewRequest,
) -> LinkPreviewResponse:
    previews = await _link_preview_service.get_many(payload.urls)
    return LinkPreviewResponse(
        items=[
            LinkPreviewItemResponse(
                url=item.url,
                title=item.title,
                description=item.description,
                image=item.image,
                favicon=item.favicon,
                site_name=item.site_name,
                published_at=item.published_at,
            )
            for item in previews
        ]
    )
