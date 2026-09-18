"""The exam-day board: what an organisation has running, right now.

Its own module rather than another two routes on `router.py`, which is at the
file cap. The split is not arbitrary: every other read model here answers "what
does this person have", and this one answers "what is happening in this
building this morning".

`OrgStaff`, not `OrgReader`: the board names every candidate and how they are
doing, which is not a thing a candidate may read about the people beside them.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionOpenerDep, get_session
from app.core.errors import Forbidden, error_responses
from app.core.events import get_event_bus
from app.core.openapi import sse_responses
from app.core.ports import ClockDep, EventBus
from app.core.sse import MEDIA_TYPE, SSE_HEADERS
from app.core.streams import StreamPrincipal
from app.core.tenancy import OrgStaff, may_run_circuit_policy, resolve_workspace
from app.features.dashboard import schemas_live, service_live, service_streams

router = APIRouter(tags=["dashboard"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/orgs/{org_slug}/live",
    response_model=schemas_live.LiveBoard,
    responses=error_responses(Forbidden),
)
async def read_live_board(workspace: OrgStaff, session: Session, clock: ClockDep) -> schemas_live.LiveBoard:
    """Every examination this organisation has running, in one request.

    The screen that did not exist: a course lead on the morning of an OSCE
    could open one circuit's console, or a list of sittings that did not say
    which were live.
    """
    return await service_live.build_live_board(session, workspace.org_id, now=clock.now())


@router.get(
    "/orgs/{org_slug}/live/stream",
    responses=sse_responses(schemas_live.LiveBoard, Forbidden),
    response_class=StreamingResponse,
)
async def stream_live_board(
    org_slug: str,
    principal: StreamPrincipal,
    bus: Annotated[EventBus, Depends(get_event_bus)],
    open_session: SessionOpenerDep,
    clock: ClockDep,
) -> StreamingResponse:
    """The board, pushed. One subscription for the whole organisation.

    Frames arrive when something changes, not on a tick: a client counts down
    from `phase_ends_at` between them rather than being told the time.
    """
    async with open_session() as session:
        workspace = await resolve_workspace(session, principal, org_slug, predicate=may_run_circuit_policy())
    return StreamingResponse(
        service_streams.live_board_stream(workspace.org_id, bus=bus, open_session=open_session, clock=clock),
        media_type=MEDIA_TYPE,
        headers=SSE_HEADERS,
    )
