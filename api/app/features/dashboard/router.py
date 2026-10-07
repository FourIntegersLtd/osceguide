"""Routes for the trainee's own dashboard and an organisation's read models on top of it."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import SessionOpenerDep, get_session
from app.core.errors import Forbidden, Unauthenticated, error_responses
from app.core.events import get_event_bus
from app.core.openapi import sse_responses
from app.core.ports import ClockDep, EventBus
from app.core.sse import MEDIA_TYPE, SSE_HEADERS
from app.core.streams import StreamPrincipal
from app.core.tenancy import OrgAdmin, OrgStaff, may_run_circuit_policy, resolve_workspace
from app.features.dashboard import (
    errors,
    schemas,
    schemas_org,
    schemas_readout,
    schemas_report,
    service,
    service_cohort,
    service_console,
    service_org,
    service_performance,
    service_readout,
    service_report,
    service_report_csv,
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
    """The trainee's home screen: access, recent attempts and progress at a glance."""
    return await service.build(session, principal.user_id, now=clock.now())


@router.get(
    "/me/performance",
    response_model=schemas.Performance,
    responses=error_responses(Unauthenticated, errors.UnknownExamError),
)
async def read_performance(
    principal: CurrentPrincipal,
    session: Session,
    exam_code: Annotated[
        str | None,
        Query(description="Which exam to report on. Defaults to the most recently attempted one."),
    ] = None,
) -> schemas.Performance:
    """How this person is doing at one exam: per domain, overall, over time.

    An exam with nothing marked yet returns an empty answer, not a 404.
    """
    return await service_performance.build(session, principal.user_id, exam_code=exam_code)


@router.get(
    "/me/sittings",
    response_model=schemas.MySittings,
    responses=error_responses(Unauthenticated),
)
async def read_my_sittings(
    principal: CurrentPrincipal, session: Session, clock: ClockDep
) -> schemas.MySittings:
    """What a trainee is rostered onto, and whether it is their turn."""
    return await service_trainee.my_sittings(
        session,
        principal.user_id,
        org_slugs={membership.org_id: membership.org_slug for membership in principal.memberships},
        now=clock.now(),
    )


@router.get(
    "/orgs/{org_slug}/dashboard",
    response_model=schemas_org.OrgDashboard,
    responses=error_responses(Forbidden),
)
async def read_org_dashboard(workspace: OrgStaff, session: Session) -> schemas_org.OrgDashboard:
    """The institutional home screen: counts, setup state and recent sittings."""
    return await service_org.build_org_dashboard(session, workspace.org_id)


@router.get(
    "/orgs/{org_slug}/supervisor/circuits",
    response_model=schemas_org.SupervisorCircuits,
    responses=error_responses(Forbidden),
)
async def read_supervisor_circuits(workspace: OrgStaff, session: Session) -> schemas_org.SupervisorCircuits:
    """The circuits assigned to the caller. Assigned, not all visible circuits."""
    return await service_org.supervisor_circuits(session, workspace.org_id, workspace.principal.user_id)


@router.get(
    "/orgs/{org_slug}/circuits/{circuit_id}/console",
    response_model=schemas_org.CircuitConsole,
    responses=error_responses(Forbidden, errors.CircuitNotFound),
)
async def read_circuit_console(
    circuit_id: uuid.UUID, workspace: OrgStaff, session: Session, clock: ClockDep
) -> schemas_org.CircuitConsole:
    """The screen an examination is run from: session, stations, trainees, staff and feedback state."""
    return await service_console.build_console(session, workspace.org_id, circuit_id, now=clock.now())


@router.get(
    "/orgs/{org_slug}/sittings/{sitting_id}/report",
    response_model=schemas_report.SittingReport,
    responses=error_responses(Forbidden, errors.SittingNotFound),
)
async def read_sitting_report(
    sitting_id: uuid.UUID, workspace: OrgAdmin, session: Session
) -> schemas_report.SittingReport:
    """The whole sitting, per candidate: stations sat, marking, reviewers' ratings and decision
    status. Org admin only — carries decisions not yet released."""
    return await service_report.build_sitting_report(session, workspace.org_id, sitting_id)


# The same report as a spreadsheet. Decisions not yet released are in it, so the access matches.
@router.get(
    "/orgs/{org_slug}/sittings/{sitting_id}/report.csv",
    response_class=Response,
    responses={
        **error_responses(Forbidden, errors.SittingNotFound),
        200: {
            "description": "The sitting's results as a CSV file.",
            "content": {"text/csv": {"schema": {"type": "string", "format": "binary"}}},
        },
    },
)
async def read_sitting_report_csv(sitting_id: uuid.UUID, workspace: OrgAdmin, session: Session) -> Response:
    payload, filename = await service_report_csv.export_sitting_results(
        session,
        org_id=workspace.org_id,
        sitting_id=sitting_id,
        actor=workspace.principal,
    )
    return Response(
        content=payload,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/orgs/{org_slug}/sittings/{sitting_id}/cohort",
    response_model=schemas_org.CohortSummary,
    responses=error_responses(Forbidden, errors.SittingNotFound, errors.NotAnExamSitting),
)
async def read_cohort_summary(
    sitting_id: uuid.UUID, workspace: OrgStaff, session: Session
) -> schemas_org.CohortSummary:
    """How this sitting's candidates compare, ranked. Completion ranks before score.

    Exam sittings only — `not_an_exam_sitting` (422) for a training one.
    """
    return await service_cohort.build_cohort_summary(session, workspace.org_id, sitting_id)


@router.get(
    "/orgs/{org_slug}/sittings/{sitting_id}/readout",
    response_model=schemas_readout.SittingReadout,
    responses=error_responses(Forbidden, errors.SittingNotFound, errors.NotAnExamSitting),
)
async def read_sitting_readout(
    sitting_id: uuid.UUID, workspace: OrgAdmin, session: Session, clock: ClockDep
) -> schemas_readout.SittingReadout:
    """The document a course lead downloads after an examination: the cohort ranked, what it
    adds up to, and what it recommends. Org admin only. Exam sittings only."""
    return await service_readout.build_readout(
        session, workspace.org_id, workspace.org_slug, sitting_id, now=clock.now()
    )


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
    clock: ClockDep,
) -> StreamingResponse:
    """The console, pushed. Every frame is a whole `CircuitConsole`, so a client renders a
    stream and a poll with the same code.

    Access is resolved against a short session of its own, not the request session, so the
    transaction does not stay open for as long as the client's connection does. Staff only, as
    the REST console is: every frame names each candidate on the circuit.
    """
    async with open_session() as session:
        workspace = await resolve_workspace(session, principal, org_slug, predicate=may_run_circuit_policy())
    return StreamingResponse(
        service_streams.console_stream(
            workspace.org_id, circuit_id, bus=bus, open_session=open_session, clock=clock
        ),
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
    clock: ClockDep,
) -> StreamingResponse:
    """The trainee portal, pushed. Replaces a five-second poll of two lists."""
    return StreamingResponse(
        service_streams.my_sittings_stream(principal, bus=bus, open_session=open_session, clock=clock),
        media_type=MEDIA_TYPE,
        headers=SSE_HEADERS,
    )
