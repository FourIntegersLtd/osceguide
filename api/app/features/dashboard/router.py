from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import SessionOpenerDep, get_session
from app.core.errors import Forbidden, Unauthenticated, error_responses
from app.core.events import get_event_bus
from app.core.openapi import sse_responses
from app.core.ports import ClockDep, EventBus
from app.core.sse import MEDIA_TYPE, SSE_HEADERS
from app.core.streams import StreamPrincipal
from app.core.tenancy import OrgReader, may_read_org_policy, resolve_workspace
from app.features.dashboard import (
    errors,
    schemas,
    schemas_org,
    service,
    service_org,
    service_streams,
    service_trainee,
)

router = APIRouter(tags=["dashboard"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/me/dashboard",
    response_model=schemas.Dashboard,
    responses=error_responses(Unauthenticated),
)
async def read_dashboard(principal: CurrentPrincipal, session: Session, clock: ClockDep) -> schemas.Dashboard:
    """One call for a screen that currently makes seven.

    A read model over several aggregates. "Dashboard" is not a domain concept —
    nothing owns one and no rule is enforced about it — which is why this slice
    has no tables and no domain module.
    """
    return await service.build(session, principal.user_id, now=clock.now())


@router.get(
    "/me/sittings",
    response_model=schemas.MySittings,
    responses=error_responses(Unauthenticated),
)
async def read_my_sittings(principal: CurrentPrincipal, session: Session) -> schemas.MySittings:
    """What a trainee is rostered onto, and whether it is their turn.

    The portal asks two endpoints every five seconds and joins them in the
    browser to answer that. The organisation slugs come from the caller's own
    token, which already carries them.
    """
    return await service_trainee.my_sittings(
        session,
        principal.user_id,
        org_slugs={m.org_id: m.org_slug for m in principal.memberships},
    )


@router.get(
    "/orgs/{org_slug}/dashboard",
    response_model=schemas_org.OrgDashboard,
    responses=error_responses(Forbidden),
)
async def read_org_dashboard(workspace: OrgReader, session: Session) -> schemas_org.OrgDashboard:
    """The institutional home screen: counts, setup state and recent sittings."""
    return await service_org.build_org_dashboard(session, workspace.org_id)


@router.get(
    "/orgs/{org_slug}/supervisor/circuits",
    response_model=schemas_org.SupervisorCircuits,
    responses=error_responses(Forbidden),
)
async def read_supervisor_circuits(workspace: OrgReader, session: Session) -> schemas_org.SupervisorCircuits:
    """The circuits assigned to the caller, whatever else they can see.

    Assigned, not visible: an administrator who supervises nothing gets an
    empty list here and reads the sittings routes for the rest.
    """
    return await service_org.supervisor_circuits(session, workspace.org_id, workspace.principal.user_id)


@router.get(
    "/orgs/{org_slug}/circuits/{circuit_id}/console",
    response_model=schemas_org.CircuitConsole,
    responses=error_responses(Forbidden, errors.CircuitNotFound),
)
async def read_circuit_console(
    circuit_id: uuid.UUID, workspace: OrgReader, session: Session
) -> schemas_org.CircuitConsole:
    """One request for the screen an examination is run from.

    Replaces a session read, a station list, a trainee list, a staff list and a
    feedback probe per slot — repeated every eight seconds while a circuit runs.
    """
    return await service_org.build_console(session, workspace.org_id, circuit_id)


@router.get(
    "/orgs/{org_slug}/circuits/{circuit_id}/console/stream",
    responses=sse_responses(schemas_org.CircuitConsole, Forbidden, errors.CircuitNotFound),
    response_class=StreamingResponse,
)
async def stream_circuit_console(
    org_slug: str,
    circuit_id: uuid.UUID,
    principal: StreamPrincipal,
    bus: Annotated[EventBus, Depends(get_event_bus)],
    open_session: SessionOpenerDep,
) -> StreamingResponse:
    """The console, pushed. The streaming form of the route above it.

    Every frame is a whole `CircuitConsole`, so a client renders a stream and a
    poll with the same code — and a missed event costs a reconnect rather than
    a wrong screen.

    Access is resolved once, before the stream opens, against a short session
    of its own: this route cannot take the request session, because that
    transaction would stay open for as long as the supervisor's tab does.
    """
    async with open_session() as session:
        workspace = await resolve_workspace(session, principal, org_slug, predicate=may_read_org_policy())
    return StreamingResponse(
        service_streams.console_stream(workspace.org_id, circuit_id, bus=bus, open_session=open_session),
        media_type=MEDIA_TYPE,
        headers=SSE_HEADERS,
    )


@router.get(
    "/me/sittings/stream",
    responses=sse_responses(schemas.MySittings, Unauthenticated),
    response_class=StreamingResponse,
)
async def stream_my_sittings(
    principal: StreamPrincipal,
    bus: Annotated[EventBus, Depends(get_event_bus)],
    open_session: SessionOpenerDep,
) -> StreamingResponse:
    """The trainee portal, pushed. Replaces a five-second poll of two lists."""
    return StreamingResponse(
        service_streams.my_sittings_stream(principal, bus=bus, open_session=open_session),
        media_type=MEDIA_TYPE,
        headers=SSE_HEADERS,
    )
