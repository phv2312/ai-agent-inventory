from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent.api.container import ApiContainer
from agent.api.exc.http import register_exception_handlers
from agent.api.v1.api import api_router


def create_app(container: ApiContainer | None = None) -> FastAPI:
    api_container = container or ApiContainer()

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        await api_container.startup()
        _app.state.container = api_container
        yield
        await api_container.shutdown()

    app = FastAPI(
        title="Agent API",
        version="1.0.0",
        description="HTTP endpoints for agent chat (SSE) and document indexing.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
