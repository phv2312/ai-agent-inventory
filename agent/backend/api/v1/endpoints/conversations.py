from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from agent.backend.api.exc.http import AppError
from agent.backend.api.v1.deps.root import get_repos
from agent.backend.api.v1.payload.conversations import (
    ContentBlockResponse,
    ConversationCreate,
    ConversationResponse,
    ConversationUpdate,
    MessageResponse,
)
import uuid

from agent.backend.api.container import Repositories
from agent.backend.db.models import MessageRole
from agent.backend.repos.protocols import ConversationRecord, MessageRecord

router = APIRouter()


def _conversation_response(record: ConversationRecord) -> ConversationResponse:
    return ConversationResponse(
        id=record.id,
        title=record.title,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _message_response(record: MessageRecord) -> MessageResponse:
    if record.content_blocks:
        blocks = [ContentBlockResponse.model_validate(b) for b in record.content_blocks]
    elif record.role == MessageRole.assistant and record.content.strip():
        blocks = [
            ContentBlockResponse(
                id=str(uuid.uuid4()),
                type="text",
                order=0,
                status="complete",
                text=record.content,
            )
        ]
    else:
        blocks = []
    return MessageResponse(
        id=record.id,
        conversation_id=record.conversation_id,
        role=record.role.value,
        content=record.content,
        content_blocks=blocks,
        mapping_evidence=record.mapping_evidence,
        created_at=record.created_at,
    )


@router.post(
    "/", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED
)
async def create_conversation(
    body: ConversationCreate,
    repos: Annotated[Repositories, Depends(get_repos)],
) -> ConversationResponse:
    record = await repos.conversations.create(body.title)
    return _conversation_response(record)


@router.get("/", response_model=list[ConversationResponse])
async def list_conversations(
    repos: Annotated[Repositories, Depends(get_repos)],
) -> list[ConversationResponse]:
    records = await repos.conversations.list()
    return [_conversation_response(r) for r in records]


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    repos: Annotated[Repositories, Depends(get_repos)],
) -> ConversationResponse:
    record = await repos.conversations.get(conversation_id)
    if record is None:
        raise AppError("NotFound", f"Conversation {conversation_id} not found", 404)
    return _conversation_response(record)


@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    body: ConversationUpdate,
    repos: Annotated[Repositories, Depends(get_repos)],
) -> ConversationResponse:
    record = await repos.conversations.update_title(conversation_id, body.title)
    if record is None:
        raise AppError("NotFound", f"Conversation {conversation_id} not found", 404)
    return _conversation_response(record)


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_conversation(
    conversation_id: str,
    repos: Annotated[Repositories, Depends(get_repos)],
) -> Response:
    deleted = await repos.conversations.delete(conversation_id)
    if not deleted:
        raise AppError("NotFound", f"Conversation {conversation_id} not found", 404)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    conversation_id: str,
    repos: Annotated[Repositories, Depends(get_repos)],
) -> list[MessageResponse]:
    record = await repos.conversations.get(conversation_id)
    if record is None:
        raise AppError("NotFound", f"Conversation {conversation_id} not found", 404)
    messages = await repos.messages.list_by_conversation(conversation_id)
    return [_message_response(m) for m in messages]
