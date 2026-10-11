"""Taking hold of a circuit that is running itself.

Every route here exists because something goes wrong on exam day, and a
supervisor is intervening. All take `OrgStaff`: an override is a staff act,
and `OrgReader` admits the candidate sitting the circuit.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.auth import CurrentPrincipal
from app.core.db import SessionDep as Session
from app.core.errors import Forbidden, error_responses
from app.core.ports import ClockDep, RoomAgents
from app.core.settings import SettingsDep
from app.core.tenancy import OrgStaffRunning
from app.features.sittings import errors, schemas, service_run
from app.features.sittings import service_control as control
from app.features.sittings import service_overrides as overrides
from app.features.sittings import service_rescue as rescue

router = APIRouter(tags=["sittings"])

_LIVE = (Forbidden, *errors.LIVE_CIRCUIT_REFUSALS)
Agents = Annotated[RoomAgents, Depends(service_run.get_room_agents)]


@router.post(
    "/orgs/{org_slug}/circuits/{circuit_id}/pause",
    response_model=schemas.CircuitRead,
    responses=error_responses(*_LIVE, errors.CircuitPausedError),
)
async def pause(
    circuit_id: uuid.UUID,
    body: schemas.Override,
    workspace: OrgStaffRunning,
    session: Session,
    principal: CurrentPrincipal,
    clock: ClockDep,
) -> schemas.CircuitRead:
    """Stop the clock. Nothing advances until it is resumed."""
    return await overrides.pause(
        session,
        workspace.org_id,
        circuit_id,
        actor=overrides.Actor.for_user(principal.user_id, body.reason),
        now=clock.now(),
    )


@router.post(
    "/orgs/{org_slug}/circuits/{circuit_id}/resume",
    response_model=schemas.CircuitRead,
    responses=error_responses(*_LIVE, errors.CircuitNotPausedError),
)
async def resume(
    circuit_id: uuid.UUID,
    body: schemas.Override,
    workspace: OrgStaffRunning,
    session: Session,
    principal: CurrentPrincipal,
    clock: ClockDep,
) -> schemas.CircuitRead:
    """Start the clock again, with the deadline pushed out by exactly the pause."""
    return await overrides.resume(
        session,
        workspace.org_id,
        circuit_id,
        actor=overrides.Actor.for_user(principal.user_id, body.reason),
        now=clock.now(),
    )


@router.post(
    "/orgs/{org_slug}/circuits/{circuit_id}/extend-clock",
    response_model=schemas.CircuitRead,
    responses=error_responses(*_LIVE),
)
async def extend_clock(
    circuit_id: uuid.UUID,
    body: schemas.ExtendClock,
    workspace: OrgStaffRunning,
    session: Session,
    principal: CurrentPrincipal,
    clock: ClockDep,
) -> schemas.CircuitRead:
    """Give this phase more time without restarting it."""
    return await overrides.extend_clock(
        session,
        workspace.org_id,
        circuit_id,
        seconds=body.seconds,
        actor=overrides.Actor.for_user(principal.user_id, body.reason),
        now=clock.now(),
    )


@router.post(
    "/orgs/{org_slug}/circuits/{circuit_id}/reset-clock",
    response_model=schemas.CircuitRead,
    responses=error_responses(*_LIVE),
)
async def reset_clock(
    circuit_id: uuid.UUID,
    body: schemas.Override,
    workspace: OrgStaffRunning,
    session: Session,
    principal: CurrentPrincipal,
    clock: ClockDep,
) -> schemas.CircuitRead:
    """Run this phase again from the top, for its full length."""
    return await overrides.reset_clock(
        session,
        workspace.org_id,
        circuit_id,
        actor=overrides.Actor.for_user(principal.user_id, body.reason),
        now=clock.now(),
    )


@router.patch(
    "/orgs/{org_slug}/circuits/{circuit_id}/auto-advance",
    response_model=schemas.CircuitRead,
    responses=error_responses(*_LIVE),
)
async def set_auto_advance(
    circuit_id: uuid.UUID,
    body: schemas.SetAutoAdvance,
    workspace: OrgStaffRunning,
    session: Session,
    principal: CurrentPrincipal,
    clock: ClockDep,
) -> schemas.CircuitRead:
    """Hand the circuit back to a human, or return it to the clock."""
    return await control.set_auto_advance(
        session,
        workspace.org_id,
        circuit_id,
        enabled=body.enabled,
        actor=overrides.Actor.for_user(principal.user_id),
        now=clock.now(),
    )


@router.post(
    "/orgs/{org_slug}/circuits/{circuit_id}/resend-patient",
    response_model=schemas.DispatchResult,
    responses=error_responses(
        *_LIVE,
        errors.NoActiveStation,
        errors.SlotNotFound,
        errors.VoiceUnavailable,
        errors.TraineeRevokedError,
        errors.MarkingNotReady,
    ),
)
async def resend_patient(
    circuit_id: uuid.UUID,
    body: schemas.Override,
    workspace: OrgStaffRunning,
    session: Session,
    principal: CurrentPrincipal,
    clock: ClockDep,
    settings: SettingsDep,
    agents: Agents,
) -> schemas.DispatchResult:
    """Put a fresh patient into the room, for the station already running."""
    return await rescue.resend_patient(
        session,
        workspace.org_id,
        circuit_id,
        agents=agents,
        settings=settings,
        actor=overrides.Actor.for_user(principal.user_id, body.reason),
        now=clock.now(),
    )


@router.post(
    "/orgs/{org_slug}/circuits/{circuit_id}/redo-station",
    response_model=schemas.CircuitRead,
    responses=error_responses(*_LIVE, errors.SlotNotFound, errors.VoiceUnavailable),
)
async def redo_station(
    circuit_id: uuid.UUID,
    body: schemas.StationOverride,
    workspace: OrgStaffRunning,
    session: Session,
    principal: CurrentPrincipal,
    clock: ClockDep,
    settings: SettingsDep,
    agents: Agents,
) -> schemas.CircuitRead:
    """Give a station back, from its reading period. The first recording survives."""
    return await rescue.redo_station(
        session,
        workspace.org_id,
        circuit_id,
        slot_id=body.slot_id,
        agents=agents,
        settings=settings,
        actor=overrides.Actor.for_user(principal.user_id, body.reason),
        now=clock.now(),
    )


@router.post(
    "/orgs/{org_slug}/circuits/{circuit_id}/jump-to",
    response_model=schemas.CircuitRead,
    responses=error_responses(*_LIVE, errors.SlotNotFound, errors.InvalidCircuitError),
)
async def jump_to(
    circuit_id: uuid.UUID,
    body: schemas.StationOverride,
    workspace: OrgStaffRunning,
    session: Session,
    principal: CurrentPrincipal,
    clock: ClockDep,
    agents: Agents,
) -> schemas.CircuitRead:
    """Move to a station out of order. Stations passed over are marked skipped."""
    return await rescue.jump_to(
        session,
        workspace.org_id,
        circuit_id,
        slot_id=body.slot_id,
        agents=agents,
        actor=overrides.Actor.for_user(principal.user_id, body.reason),
        now=clock.now(),
    )


@router.get(
    "/orgs/{org_slug}/circuits/{circuit_id}/interventions",
    response_model=schemas.Interventions,
    responses=error_responses(Forbidden, errors.CircuitNotFound),
)
async def list_interventions(
    circuit_id: uuid.UUID, workspace: OrgStaffRunning, session: Session
) -> schemas.Interventions:
    """Everything a human did to this examination, and why."""
    return await overrides.list_interventions(session, workspace.org_id, circuit_id)
