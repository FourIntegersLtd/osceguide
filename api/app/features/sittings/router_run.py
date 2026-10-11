"""Running a live examination: the one manual start, and every override.

Separate from `router.py`, which schedules sittings and builds circuits. These
are the routes somebody has open on a tablet while twelve candidates are in
rooms, and they take `OrgStaff` rather than `OrgReader` — the latter admits the
trainee sitting the circuit, who could then end it.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.auth import CurrentPrincipal
from app.core.db import SessionDep as Session
from app.core.errors import Forbidden, Unauthenticated, error_responses
from app.core.ports import ClockDep, RoomAgents, VoiceTokens
from app.core.settings import SettingsDep
from app.core.tenancy import OrgStaff, OrgStaffRunning, OrgSuspended
from app.features.sittings import errors, schemas, service_brief, service_circuit, service_join, service_run
from app.features.sittings import service_control as control
from app.features.sittings import service_overrides as overrides

router = APIRouter(tags=["sittings"])

Agents = Annotated[RoomAgents, Depends(service_run.get_room_agents)]
Tokens = Annotated[VoiceTokens, Depends(service_join.get_voice_tokens)]

_LIVE = (Forbidden, *errors.LIVE_CIRCUIT_REFUSALS)


@router.post(
    "/orgs/{org_slug}/circuits/{circuit_id}/start",
    response_model=schemas.CircuitRead,
    responses=error_responses(
        Forbidden,
        errors.CircuitNotFound,
        errors.CircuitAlreadyEndedError,
        errors.SittingLockedError,
        errors.LeadCannotRun,
        errors.ProgrammeNotActive,
        OrgSuspended,
    ),
)
async def start_circuit(
    circuit_id: uuid.UUID, workspace: OrgStaff, session: Session, clock: ClockDep
) -> schemas.CircuitRead:
    """Open the room and start the first station's reading time.

    The only manual act left in an examination: from here the clock carries it.
    """
    return await service_run.start_circuit(session, workspace.org_id, circuit_id, now=clock.now())


@router.post(
    "/orgs/{org_slug}/circuits/{circuit_id}/end",
    response_model=schemas.CircuitRead,
    # Ending takes the patient out of the room, so LiveKit being unreachable
    # is a refusal this route can answer with.
    responses=error_responses(Forbidden, errors.CircuitNotFound, errors.VoiceUnavailable),
)
async def end_circuit(
    circuit_id: uuid.UUID,
    workspace: OrgStaffRunning,
    session: Session,
    clock: ClockDep,
    agents: Agents,
    body: schemas.Override | None = None,
) -> schemas.CircuitRead:
    """Stop the whole examination, wherever it had got to. The optional reason is audited."""
    return await service_run.end_circuit_by(
        session,
        workspace.org_id,
        circuit_id,
        agents=agents,
        now=clock.now(),
        actor=workspace.principal,
        reason=body.reason if body is not None else None,
    )


@router.post(
    "/orgs/{org_slug}/circuits/{circuit_id}/advance",
    response_model=schemas.CircuitRead,
    responses=error_responses(*_LIVE, errors.CircuitPausedError, errors.VoiceUnavailable),
)
async def advance(
    circuit_id: uuid.UUID,
    body: schemas.Override,
    workspace: OrgStaffRunning,
    session: Session,
    principal: CurrentPrincipal,
    clock: ClockDep,
    settings: SettingsDep,
    agents: Agents,
) -> schemas.CircuitRead:
    """ "This phase is done." Whatever the clock was counting, move on.

    Deliberately not "end the station": during a reading period it brings the
    patient in, during a break it starts the next station. One button that
    always means the same thing.
    """
    return await control.advance_now(
        session,
        workspace.org_id,
        circuit_id,
        agents=agents,
        settings=settings,
        actor=overrides.Actor.for_user(principal.user_id, body.reason),
        now=clock.now(),
    )


@router.get(
    "/orgs/{org_slug}/circuits/{circuit_id}/edit-lock",
    response_model=schemas.EditLock,
    responses=error_responses(Forbidden, errors.CircuitNotFound),
)
async def read_edit_lock(
    circuit_id: uuid.UUID, workspace: OrgStaffRunning, session: Session
) -> schemas.EditLock:
    """Whether the slots may still be rebuilt, and why not.

    Asked rather than discovered: the console needs this before it offers an
    edit, not after somebody has typed one.
    """
    return await service_circuit.read_edit_lock(session, workspace.org_id, circuit_id)


@router.post(
    "/orgs/{org_slug}/circuits/{circuit_id}/observer-token",
    response_model=schemas.RoomGrant,
    responses=error_responses(*_LIVE, errors.VoiceUnavailable),
)
async def observer_token(
    circuit_id: uuid.UUID,
    workspace: OrgStaffRunning,
    session: Session,
    principal: CurrentPrincipal,
    settings: SettingsDep,
    tokens: Tokens,
) -> schemas.RoomGrant:
    """An examiner's way into a candidate's room: they hear it, and cannot be heard."""
    return await service_join.observer_token(
        session,
        workspace.org_id,
        circuit_id,
        user_id=principal.user_id,
        tokens=tokens,
        settings=settings,
    )


@router.post(
    "/me/circuits/{circuit_id}/join-token",
    response_model=schemas.RoomGrant,
    responses=error_responses(
        Unauthenticated,
        errors.CircuitNotFound,
        errors.CircuitNotLive,
        errors.VoiceUnavailable,
        OrgSuspended,
        errors.TraineeRevokedError,
        errors.MarkingNotReady,
        errors.TraineeNotOnRosterError,
    ),
)
async def join_token(
    circuit_id: uuid.UUID,
    principal: CurrentPrincipal,
    session: Session,
    settings: SettingsDep,
    tokens: Tokens,
) -> schemas.RoomGrant:
    """A candidate's way in, at the start of the circuit rather than per station.

    Being rostered onto the circuit is the permission, so this is not under an
    organisation's path: a candidate should not have to name their institution
    to sit its examination.
    """
    return await service_join.join_token_for_trainee(
        session, circuit_id, user_id=principal.user_id, tokens=tokens, settings=settings
    )


@router.get(
    "/me/slots/{slot_id}/brief",
    response_model=schemas.SlotBriefRead,
    responses=error_responses(Unauthenticated, errors.SlotNotFound, errors.CircuitNotStarted),
)
async def read_slot_brief(
    slot_id: uuid.UUID, principal: CurrentPrincipal, session: Session
) -> schemas.SlotBriefRead:
    """The reading brief for one of the caller's slots, once the circuit has reached it.

    Whatever the station's source (the org's own or the platform library), and
    before the patient is dispatched — the attempt's brief exists only after.
    """
    return await service_brief.brief_for_trainee(session, slot_id, user_id=principal.user_id)
