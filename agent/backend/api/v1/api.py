from fastapi import APIRouter

from agent.backend.api.v1.endpoints import (
    chats,
    chunks,
    collections,
    conversations,
    references,
)

api_router = APIRouter()
api_router.include_router(
    conversations.router, prefix="/conversations", tags=["Conversations"]
)
api_router.include_router(chats.router, prefix="/chats", tags=["Chats"])
api_router.include_router(
    collections.router, prefix="/collections", tags=["Collections"]
)
api_router.include_router(references.router, prefix="/references", tags=["References"])
api_router.include_router(chunks.router, prefix="/chunks", tags=["Chunks"])
