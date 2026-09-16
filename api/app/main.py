"""Application factory.

Everything that composes the app lives here and nowhere else: settings,
logging, middleware, error handlers, and the router registry. A feature slice
exposes a `router`; this file mounts it. Nothing else may call
`include_router`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.core.db import dispose_engine
from app.core.errors import register_error_handlers
from app.core.logging import RequestContextMiddleware, configure_logging, get_logger
from app.core.openapi import TAGS, operation_id
from app.core.redis import close_redis
from app.core.settings import get_settings
from app.features import health

API_V1_PREFIX = "/api/v1"
WORKER_PREFIX = "/api/worker"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    get_logger(__name__).info("starting", env=settings.app_env.value, version=__version__)
    yield
    await close_redis()
    await dispose_engine()


def api_v1_router() -> APIRouter:
    """Public, versioned API. Add each slice's router here."""
    router = APIRouter()
    return router


def worker_router() -> APIRouter:
    """Routes the LiveKit workers call. Each is guarded by `require_worker_secret`."""
    router = APIRouter()
    return router


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        lifespan=lifespan,
        openapi_tags=TAGS,
        generate_unique_id_function=operation_id,
        docs_url="/docs" if not settings.is_deployed else None,
        redoc_url=None,
    )
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)

    app.include_router(health.router)
    app.include_router(api_v1_router(), prefix=API_V1_PREFIX)
    app.include_router(worker_router(), prefix=WORKER_PREFIX)
    return app


app = create_app()
