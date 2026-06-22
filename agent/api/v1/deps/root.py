from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from agent.api.container import ApiContainer, Repositories
from agent.api.settings import ApiSettings


def get_container(request: Request) -> ApiContainer:
    return request.app.state.container


def get_settings(
    container: Annotated[ApiContainer, Depends(get_container)],
) -> ApiSettings:
    return container.settings


async def get_session(
    container: Annotated[ApiContainer, Depends(get_container)],
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_repos(
    session: Annotated[AsyncSession, Depends(get_session)],
    container: Annotated[ApiContainer, Depends(get_container)],
) -> Repositories:
    return container.repos(session)
