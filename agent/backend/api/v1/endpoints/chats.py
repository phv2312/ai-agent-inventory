import json
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from sse_starlette import ServerSentEvent
from sse_starlette.sse import EventSourceResponse

from agent.backend.api.container import ApiContainer
from agent.backend.api.exc.http import AppError
from agent.backend.api.v1.deps.root import get_container, get_settings
from agent.backend.api.settings import ApiSettings
from agent.backend.db.models import MessageRole
from agent.backend.chatstream.core import ChatStreamService
from agent.backend.chatstream.models import (
    NameSuggestionData,
    is_untitled_conversation,
)
from agent.backend.api.v1.docs.description import Descriptions
from agent.backend.api.v1.docs.examples import load_text
from agent.backend.api.v1.docs.openapi_helpers import sse_example
from agent.backend.api.v1.payload.chats import (
    LinkPreviewItemResponse,
    LinkPreviewRequest,
    LinkPreviewResponse,
)
from agent.backend.services.link_preview import LinkPreviewService
from agent.backend.services.scope import resolve_scope_reference_ids
from agent.core.models.messages import AssistantMessage, UserMessage

router = APIRouter()
_link_preview_service = LinkPreviewService()


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

    chat_service = ChatStreamService(container.agent)

    async def event_generator() -> AsyncGenerator[ServerSentEvent, None]:
        async for event in chat_service.stream(
            message=text,
            file_ids=file_ids,
            history=history,
            top_k=top_k,
            web_search_enabled=web_search_enabled,
            system_prompt=system_prompt,
            # keep track of user-message id for easier to trace the response
            request_id=user_message.id,
        ):
            if await request.is_disconnected():
                return
            yield event

        if await request.is_disconnected():
            return

        state = chat_service.last_state
        has_output = bool(state.answer_text.strip()) or bool(state.content_blocks)
        if not has_output:
            return

        content = state.answer_text
        mapping = ChatStreamService.build_mapping_evidence(
            content,
            state.validated_chunk_ids,
        )
        content_blocks = [
            block.model_dump(mode="json") for block in state.content_blocks
        ] or None

        async with container.session_factory() as session:
            repos = container.repos(session)
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
                conversation_title, text
            )
            if suggestion is not None:
                yield suggestion
                if (
                    is_untitled_conversation(conversation_title)
                    and suggestion.data is not None
                ):
                    data = json.loads(suggestion.data)
                    name = NameSuggestionData.model_validate(data).name
                    await repos.conversations.update_title(conversation_id, name)
            await session.commit()

    return EventSourceResponse(event_generator())


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
