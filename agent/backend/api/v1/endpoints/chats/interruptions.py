import json
from collections.abc import AsyncGenerator
from typing import Annotated, Any, Literal

import anyio
import structlog
from fastapi import APIRouter, Depends, Request
from sqlalchemy.exc import IntegrityError
from sse_starlette import ServerSentEvent
from sse_starlette.sse import EventSourceResponse

from agent.backend.api.container import ApiContainer
from agent.backend.api.exc.http import AppError
from agent.backend.api.v1.deps.root import get_container
from agent.backend.api.v1.endpoints.chats.shared import (
    interruption_event,
    persist_completed_response,
)
from agent.backend.api.v1.payload.chats import (
    InterruptionDecision,
    InterruptionDecisionRequest,
)
from agent.backend.chatstream.core import ChatStreamService
from agent.backend.chatstream.models import InterruptionEventData
from agent.core._agent import RunInput
from agent.core._agent.parser.core import ChatRunStatus, Interruption

router = APIRouter()
log = structlog.get_logger(__name__)


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
            log.warning("conversation_not_found", conversation_id=conversation_id)
            raise AppError("NotFound", f"Conversation {conversation_id} not found", 404)
        pending = await repos.pending_runs.get(conversation_id)
        history = await repos.pending_runs.history(conversation_id)
        if pending and any(
            row["version"] == pending.version
            and {item["id"] for item in row["interruptions"]}
            == {item["id"] for item in pending.interruptions}
            for row in history
        ):
            pending = None
    if pending is None:
        log.warning("pending_interruption_not_found", conversation_id=conversation_id)
        raise AppError("NotFound", "There is no agent plan awaiting review", 404)
    log.info(
        "pending_interruption_retrieved",
        conversation_id=conversation_id,
        pending_version=pending.version,
        interruption_count=len(pending.interruptions),
    )
    return InterruptionEventData.model_validate(
        {
            "conversation_id": conversation_id,
            "version": pending.version,
            "interruptions": pending.interruptions,
        }
    )


@router.get("/{conversation_id}/interruptions/history")
async def interruption_history(
    conversation_id: str,
    container: Annotated[ApiContainer, Depends(get_container)],
) -> list[dict[str, Any]]:
    async with container.session_factory() as session:
        repos = container.repos(session)
        if await repos.conversations.get(conversation_id) is None:
            raise AppError("NotFound", "Conversation not found", 404)
        return await repos.pending_runs.history(conversation_id)


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
            log.warning("conversation_not_found", conversation_id=conversation_id)
            raise AppError("NotFound", f"Conversation {conversation_id} not found", 404)
        pending = await repos.pending_runs.get(conversation_id)
        if pending is None:
            log.warning(
                "pending_interruption_not_found",
                conversation_id=conversation_id,
            )
            raise AppError("NotFound", "There is no agent plan awaiting review", 404)
        expected_ids = {item["id"] for item in pending.interruptions}
        if (
            pending.version != payload.version
            or set(payload.interruption_ids) != expected_ids
        ):
            log.warning(
                "pending_interruption_stale",
                conversation_id=conversation_id,
                requested_version=payload.version,
                current_version=pending.version,
            )
            raise AppError(
                "StaleInterruption",
                "The pending interruption changed; reload it before responding",
                409,
            )

        try:
            await repos.pending_runs.record_response(
                pending, payload.decision, payload.feedback or ""
            )
        except IntegrityError as exc:
            raise AppError(
                "InterruptionConflict", "This plan already has a response", 409
            ) from exc

        if payload.decision == InterruptionDecision.CANCEL:
            deleted = await repos.pending_runs.delete(
                conversation_id,
                payload.version,
            )
            if not deleted:
                log.warning(
                    "pending_interruption_conflict",
                    conversation_id=conversation_id,
                    pending_version=payload.version,
                )
                raise AppError(
                    "InterruptionConflict",
                    "The pending interruption is already being handled",
                    409,
                )
            await session.commit()
            log.info(
                "pending_interruption_cancelled",
                conversation_id=conversation_id,
                pending_version=payload.version,
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
    log.info(
        "pending_interruption_resume_started",
        conversation_id=conversation_id,
        pending_version=payload.version,
        decision=resume_decision,
        has_feedback=bool(payload.feedback),
    )

    async def resumed_events() -> AsyncGenerator[ServerSentEvent, None]:
        try:
            interruption: Interruption | None = None
            async for event in chat_service.resume(
                snapshot=snapshot,
                state_json=pending.state_json,
                decision=resume_decision,
                feedback=payload.feedback or "",
            ):
                if isinstance(event, Interruption):
                    interruption = event
                    continue
                if await request.is_disconnected():
                    log.info(
                        "pending_interruption_resume_disconnected",
                        conversation_id=conversation_id,
                        pending_version=payload.version,
                    )
                    return
                yield event

            state = chat_service.last_state
            if state.status not in {
                ChatRunStatus.INTERRUPTED,
                ChatRunStatus.COMPLETED,
            }:
                log.warning(
                    "pending_interruption_resume_ended_without_resolution",
                    conversation_id=conversation_id,
                    pending_version=payload.version,
                    status=state.status.value,
                )
                return

            if interruption is not None:
                if (
                    interruption.serialized_run_state is None
                    or not interruption.interruptions
                ):
                    log.warning(
                        "pending_interruption_resume_invalid",
                        conversation_id=conversation_id,
                        pending_version=payload.version,
                    )
                    return
                async with container.session_factory() as session:
                    repos = container.repos(session)
                    revised = await repos.pending_runs.replace(
                        conversation_id=conversation_id,
                        version=payload.version,
                        state_json=interruption.serialized_run_state,
                        interruptions=[
                            item.model_dump(mode="json")
                            for item in interruption.interruptions
                        ],
                    )
                    await session.commit()
                if revised is None:
                    log.warning(
                        "pending_interruption_replace_conflict",
                        conversation_id=conversation_id,
                        pending_version=payload.version,
                    )
                    return
                log.info(
                    "pending_interruption_revised",
                    conversation_id=conversation_id,
                    previous_version=payload.version,
                    pending_version=revised.version,
                    interruption_count=len(interruption.interruptions),
                )
                yield interruption_event(
                    conversation_id,
                    revised.version,
                    interruption.interruptions,
                )
                return

            suggestion = await persist_completed_response(
                container=container,
                chat_service=chat_service,
                conversation_id=conversation_id,
                conversation_title=conversation.title,
                user_message=snapshot.query,
                pending_version=payload.version,
            )
            if suggestion is not None:
                yield suggestion
        finally:
            # A response is durable even when execution fails or the client leaves.
            # Retire only this version; a revised pending plan must survive.
            with anyio.CancelScope(shield=True):
                async with container.session_factory() as session:
                    await container.repos(session).pending_runs.delete(
                        conversation_id, payload.version, pending.user_message_id
                    )
                    await session.commit()

    return EventSourceResponse(resumed_events())
