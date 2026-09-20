from fastapi import APIRouter

from agent.backend.api.v1.endpoints.chats import core, interruptions, link_previews

router = APIRouter()
router.include_router(core.router)
router.include_router(interruptions.router)
router.include_router(link_previews.router)
