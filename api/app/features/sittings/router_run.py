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
from app.features.sittings import (
    errors,
    schemas,
    service_brief,
    service_circuit,
    service_floor,
    service_join,
    service_peer,
    service_run,
    service_scheme,
)
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
    responses=error_responses(*_LIVE, errors.NotYourStation, errors.VoiceUnavailable),
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
        role=workspace.role,
    )


@router.post(
    "/me/circuits/{circuit_id}/join-token",
    response_model=schemas.RoomGrant,
    responses=error_responses(
        Unauthenticated,
        errors.CircuitNotFound,
        errors.CircuitNotLive,
        errors.CandidateMarkedAbsent,
        errors.VoiceUnavailable,
        OrgSuspended,
        errors.TraineeRevokedError,
        errors.MarkingNotReady,
        errors.TraineeNotOnRosterError,
        errors.JoinNotOpen,
    ),
)
async def join_token(
    circuit_id: uuid.UUID,
    principal: CurrentPrincipal,
    session: Session,
    settings: SettingsDep,
    tokens: Tokens,
    clock: ClockDep,
) -> schemas.RoomGrant:
    """A candidate's way in, at the start of the circuit rather than per station.

    Being rostered onto the circuit is the permission, so this is not under an
    organisation's path: a candidate should not have to name their institution
    to sit its examination.
    """
    return await service_join.join_token_for_trainee(
        session, circuit_id, user_id=principal.user_id, tokens=tokens, settings=settings, now=clock.now()
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


_ROOM = (
    Forbidden,
    errors.CircuitNotFound,
    errors.NotATrainingCircuit,
    errors.CircuitNotLive,
    errors.VoiceUnavailable,
)


@router.post(
    "/orgs/{org_slug}/circuits/{circuit_id}/floor",
    response_model=schemas.CircuitRead,
    responses=error_responses(*_ROOM),
)
async def set_floor(
    circuit_id: uuid.UUID,
    body: schemas.FloorChange,
    workspace: OrgStaffRunning,
    session: Session,
    clock: ClockDep,
    agents: Agents,
) -> schemas.CircuitRead:
    """Training: open the floor (everyone may speak) or close it (the turn and the supervisor only)."""
    return await service_floor.set_floor(
        session,
        workspace.org_id,
        circuit_id,
        open_floor=body.open,
        agents=agents,
        actor=workspace.principal,
        now=clock.now(),
    )


@router.post(
    "/orgs/{org_slug}/circuits/{circuit_id}/participants/{identity}/mic",
    response_model=schemas.CircuitRead,
    responses=error_responses(*_ROOM),
)
async def set_participant_mic(
    circuit_id: uuid.UUID,
    identity: str,
    body: schemas.MicChange,
    workspace: OrgStaffRunning,
    session: Session,
    clock: ClockDep,
    agents: Agents,
) -> schemas.CircuitRead:
    """Training: switch one person's microphone on or off while they stay in the room."""
    return await service_floor.set_participant_mic(
        session,
        workspace.org_id,
        circuit_id,
        identity=identity,
        allowed=body.allowed,
        agents=agents,
        actor=workspace.principal,
        now=clock.now(),
    )


@router.post(
    "/orgs/{org_slug}/circuits/{circuit_id}/room/close",
    response_model=schemas.CircuitRead,
    responses=error_responses(*_ROOM, errors.CircuitNotEnded),
)
async def close_room(
    circuit_id: uuid.UUID, workspace: OrgStaffRunning, session: Session, clock: ClockDep, agents: Agents
) -> schemas.CircuitRead:
    """Training: after End, close the room and disconnect everyone."""
    return await service_floor.close_room(
        session,
        workspace.org_id,
        circuit_id,
        agents=agents,
        actor=workspace.principal,
        now=clock.now(),
    )


@router.get(
    "/orgs/{org_slug}/circuits/{circuit_id}/scheme",
    response_model=schemas.SchemeRead,
    responses=error_responses(
        Forbidden, errors.CircuitNotFound, errors.SchemeNotShown, errors.NoActiveStation
    ),
)
async def circuit_scheme(circuit_id: uuid.UUID, workspace: OrgStaff, session: Session) -> schemas.SchemeRead:
    """Training: the marking scheme of the station running now, for the supervisor's rail."""
    return await service_scheme.scheme_for_staff(session, workspace.org_id, circuit_id)


@router.get(
    "/me/circuits/{circuit_id}/scheme",
    response_model=schemas.SchemeRead,
    responses=error_responses(
        Unauthenticated,
        errors.CircuitNotFound,
        errors.SchemeNotShown,
        errors.NoActiveStation,
        errors.TraineeRevokedError,
    ),
)
async def my_circuit_scheme(
    circuit_id: uuid.UUID, principal: CurrentPrincipal, session: Session
) -> schemas.SchemeRead:
    """Training: the scheme for a trainee waiting their turn (never the one with the turn)."""
    return await service_scheme.scheme_for_trainee(session, circuit_id, user_id=principal.user_id)


@router.get(
    "/me/slots/{slot_id}/peer-marks",
    response_model=schemas.PeerMarksRead,
    responses=error_responses(Unauthenticated, errors.SlotNotFound),
)
async def read_my_peer_marks(
    slot_id: uuid.UUID, principal: CurrentPrincipal, session: Session
) -> schemas.PeerMarksRead:
    """What the trainees who watched my practice turn marked; empty until its feedback is shared."""
    return await service_peer.read_my_peer_marks(session, slot_id=slot_id, user_id=principal.user_id)


@router.put(
    "/me/circuits/{circuit_id}/slots/{slot_id}/peer-marks",
    response_model=schemas.PeerMarksRead,
    responses=error_responses(
        Unauthenticated,
        errors.CircuitNotFound,
        errors.SlotNotFound,
        errors.PeerMarksNotAllowed,
        errors.PeerMarksOwnTurn,
        errors.PeerMarksClosed,
        errors.PeerMarkItemUnknown,
        errors.PeerMarkRatingUnknown,
        errors.TraineeRevokedError,
    ),
)
async def save_peer_marks(
    circuit_id: uuid.UUID,
    slot_id: uuid.UUID,
    body: schemas.SavePeerMarks,
    principal: CurrentPrincipal,
    session: Session,
) -> schemas.PeerMarksRead:
    """A trainee watching another's turn saves their marks on it; yours only, per item."""
    return await service_peer.save_peer_marks(
        session, circuit_id, slot_id, user_id=principal.user_id, marks=body.marks
    )


@router.get(
    "/orgs/{org_slug}/circuits/{circuit_id}/slots/{slot_id}/peer-marks",
    response_model=schemas.PeerMarksRead,
    responses=error_responses(Forbidden, errors.CircuitNotFound, errors.SlotNotFound),
)
async def circuit_peer_marks(
    circuit_id: uuid.UUID, slot_id: uuid.UUID, workspace: OrgStaff, session: Session
) -> schemas.PeerMarksRead:
    """Every watching trainee's marks on one turn, live, for the supervisor's panel."""
    return await service_peer.peer_marks_for_staff(session, workspace.org_id, circuit_id, slot_id)
