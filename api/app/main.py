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
from app.composition import bind_seams
from app.core.db import dispose_engine
from app.core.errors import register_error_handlers
from app.core.logging import RequestContextMiddleware, configure_logging, get_logger
from app.core.observability import configure_sentry
from app.core.openapi import (
    TAGS,
    document_shared_auth_errors,
    install_error_catalogue,
    install_me_event_schema,
    operation_id,
)
from app.core.redis import close_redis
from app.core.security_headers import SecurityHeadersMiddleware
from app.core.settings import get_settings
from app.features import health
from app.features.assistant.router import router as assistant_router
from app.features.assistant.router_help import router as help_router
from app.features.assistant.router_worker import router as assistant_worker_router
from app.features.attempts.router import router as attempts_router
from app.features.attempts.router_coverage import router as attempts_coverage_router
from app.features.attempts.router_platform import router as platform_attempts_router
from app.features.attempts.router_roleplay import router as attempts_roleplay_router
from app.features.attempts.router_worker import router as attempts_worker_router
from app.features.billing.router import router as billing_router
from app.features.billing.router_invoices import router as invoices_router
from app.features.billing.router_platform import router as platform_billing_router
from app.features.catalog.router import router as catalog_router
from app.features.community.router import router as community_router
from app.features.community.router_platform import router as community_platform_router
from app.features.cv.router import router as cv_router
from app.features.dashboard.router import router as dashboard_router
from app.features.dashboard.router_achievements import router as achievements_router
from app.features.dashboard.router_live import router as live_board_router
from app.features.dashboard.router_platform import router as platform_directory_router
from app.features.entitlements.router import router as entitlements_router
from app.features.entitlements.router_platform import router as platform_entitlements_router
from app.features.generation.router import router as generation_router
from app.features.growth.router import router as growth_router
from app.features.health.router_platform import router as platform_health_router
from app.features.identity.router import router as identity_router
from app.features.identity.router_me import router as identity_me_router
from app.features.marketplace.router import router as marketplace_router
from app.features.media.router import router as media_router
from app.features.media_production.router import router as media_production_router
from app.features.peer_practice.router import router as peer_practice_router
from app.features.peer_practice.router_sessions import router as peer_practice_sessions_router
from app.features.public_site.router import router as public_site_router
from app.features.results.router import router as results_router
from app.features.reviews.router import router as reviews_router
from app.features.roster.router import router as roster_router
from app.features.roster.router_scim import router as scim_router
from app.features.rubrics.router import router as rubrics_router
from app.features.rubrics.router_org import router as org_rubrics_router
from app.features.sittings.router import router as sittings_router
from app.features.sittings.router_overrides import router as circuit_overrides_router
from app.features.sittings.router_run import router as circuit_run_router
from app.features.sso.router import router as sso_router
from app.features.station_sets.router import router as station_sets_router
from app.features.station_sets.router_platform import router as platform_station_sets_router
from app.features.stations.router import router as stations_router
from app.features.stations.router_flags import router as station_flags_router
from app.features.stations.router_generation_profiles import router as station_generation_profiles_router
from app.features.stations.router_photos import router as station_photos_router
from app.features.stations.router_platform import router as platform_stations_router
from app.features.stations.router_platform_templates import router as platform_station_templates_router
from app.features.stations.router_templates import router as station_templates_router
from app.features.tenancy.router import router as tenancy_router
from app.features.tenancy.router_platform import router as platform_console_router
from app.features.tenancy.router_platform_members import router as platform_members_router
from app.features.tenancy.router_platform_users import router as platform_users_router
from app.features.tutor_memory.router import router as tutor_memory_router
from app.features.tutor_memory.router_worker import router as tutor_memory_worker_router
from app.features.voice.router import router as voice_router
from app.features.voice.router_platform import router as platform_voice_router
from app.features.voice.router_worker import router as voice_worker_router

API_V1_PREFIX = "/api/v1"
WORKER_PREFIX = "/api/worker"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Log the app's start, then close Redis and the database engine on shutdown."""
    settings = get_settings()
    get_logger(__name__).info("starting", env=settings.app_env.value, version=__version__)
    yield
    await close_redis()
    await dispose_engine()


def api_v1_router() -> APIRouter:
    """Public, versioned API. Add each slice's router here."""
    router = APIRouter()
    router.include_router(identity_router)
    router.include_router(identity_me_router)
    router.include_router(tenancy_router)
    router.include_router(platform_console_router)
    router.include_router(platform_users_router)
    router.include_router(platform_members_router)
    router.include_router(catalog_router)
    router.include_router(rubrics_router)
    router.include_router(org_rubrics_router)
    router.include_router(stations_router)
    router.include_router(station_flags_router)
    router.include_router(station_templates_router)
    router.include_router(station_generation_profiles_router)
    router.include_router(platform_stations_router)
    router.include_router(station_photos_router)
    router.include_router(platform_station_templates_router)
    router.include_router(attempts_router)
    router.include_router(attempts_coverage_router)
    router.include_router(attempts_roleplay_router)
    router.include_router(platform_attempts_router)
    router.include_router(entitlements_router)
    router.include_router(platform_entitlements_router)
    router.include_router(voice_router)
    router.include_router(platform_voice_router)
    router.include_router(platform_health_router)
    router.include_router(sittings_router)
    router.include_router(circuit_run_router)
    router.include_router(circuit_overrides_router)
    router.include_router(roster_router)
    router.include_router(scim_router)
    router.include_router(reviews_router)
    router.include_router(results_router)
    router.include_router(billing_router)
    router.include_router(platform_billing_router)
    router.include_router(invoices_router)
    router.include_router(station_sets_router)
    router.include_router(platform_station_sets_router)
    router.include_router(dashboard_router)
    router.include_router(achievements_router)
    router.include_router(platform_directory_router)
    router.include_router(live_board_router)
    router.include_router(assistant_router)
    router.include_router(help_router)
    router.include_router(marketplace_router)
    router.include_router(community_router)
    router.include_router(community_platform_router)
    router.include_router(cv_router)
    router.include_router(peer_practice_router)
    router.include_router(peer_practice_sessions_router)
    router.include_router(growth_router)
    router.include_router(generation_router)
    router.include_router(media_router)
    router.include_router(media_production_router)
    router.include_router(sso_router)
    router.include_router(public_site_router)
    router.include_router(tutor_memory_router)
    return router


def worker_router() -> APIRouter:
    """Routes the LiveKit workers call. Each is guarded by `require_worker_secret`."""
    router = APIRouter()
    router.include_router(attempts_worker_router)
    router.include_router(assistant_worker_router)
    router.include_router(voice_worker_router)
    router.include_router(tutor_memory_worker_router)
    return router


def create_app() -> FastAPI:
    """Build the FastAPI app: settings, logging, middleware, every slice's router and its error catalogue."""
    settings = get_settings()
    configure_logging(settings)
    if configure_sentry(settings):
        get_logger(__name__).info("error reporting on", environment=settings.app_env.value)

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        lifespan=lifespan,
        openapi_tags=TAGS,
        generate_unique_id_function=operation_id,
        docs_url="/docs" if not settings.is_deployed else None,
        redoc_url=None,
        # The schema drives local docs and the frontend's type generation, both
        # of which run against a non-deployed instance. In a deployed
        # environment it is turned off so the full route inventory is not
        # published to an unauthenticated caller.
        openapi_url=None if settings.is_deployed else "/openapi.json",
    )
    app.add_middleware(SecurityHeadersMiddleware, deployed=settings.is_deployed)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)

    bind_seams()

    app.include_router(health.router)
    app.include_router(api_v1_router(), prefix=API_V1_PREFIX)
    app.include_router(worker_router(), prefix=WORKER_PREFIX)

    # After the routers, so every slice's `errors.py` has been imported and the
    # catalogue walk sees the whole hierarchy.
    document_shared_auth_errors(app)
    install_error_catalogue(app)
    install_me_event_schema(app)
    return app


app = create_app()
