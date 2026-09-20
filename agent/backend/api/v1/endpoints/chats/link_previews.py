import structlog
from fastapi import APIRouter

from agent.backend.api.v1.payload.chats import (
    LinkPreviewItemResponse,
    LinkPreviewRequest,
    LinkPreviewResponse,
)
from agent.backend.services.link_preview import LinkPreviewService

router = APIRouter()
log = structlog.get_logger(__name__)
_link_preview_service = LinkPreviewService()


@router.post(
    "/link-previews",
    summary="Fetch link preview metadata",
    response_model=LinkPreviewResponse,
)
async def get_link_previews(
    payload: LinkPreviewRequest,
) -> LinkPreviewResponse:
    previews = await _link_preview_service.get_many(payload.urls)
    log.info(
        "link_previews_fetched",
        requested_count=len(payload.urls),
        result_count=len(previews),
    )
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
