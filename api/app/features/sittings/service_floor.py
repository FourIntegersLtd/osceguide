"""Running a training room: who may speak, the open floor, and closing it after End.

A training circuit is a video room for the group (see `floor.py` for the one rule). The rule is
in every token, so a rejoin corrects it; this module re-applies it to the people already in the
room whenever the turn or the floor changes, and gives the supervisor the controls.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from types import SimpleNamespace

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.core.errors import InvalidInput
from app.core.events import run_after_commit
from app.core.logging import get_logger
from app.core.ports import AGENT_PREFIX, RoomAgents
from app.features.sittings import announcements, errors, floor, repository, repository_run
from app.features.sittings.models import Circuit
from app.features.sittings.overrides import (
    FLOOR_CHANGED,
    MIC_CHANGED,
    ROOM_CLOSED,
    Actor,
    write_intervention,
)
from app.features.sittings.schemas import CircuitRead
from app.features.sittings.service import _require_circuit, read_circuit

log = get_logger(__name__)


async def is_training(session: AsyncSession, circuit_id: uuid.UUID) -> bool:
    """Whether the circuit's sitting is a training one. A vanished circuit is exam-strict (not training)."""
    return await repository_run.sitting_mode_for_circuit(session, circuit_id) == "training"


async def active_trainee_id(session: AsyncSession, org_id: uuid.UUID, circuit: Circuit) -> uuid.UUID | None:
    """Whose turn it is: the active slot's trainee (a `users.id`), nobody once the circuit has ended."""
    if circuit.ended_at is not None or circuit.active_slot_id is None:
        return None
    slot = await repository.slot_by_id(session, org_id, circuit.active_slot_id)
    return slot.trainee_id if slot is not None else None


async def sync_mics(
    session: AsyncSession, org_id: uuid.UUID, circuit: Circuit, *, agents: RoomAgents
) -> None:
    """Re-apply the mic rule to everyone already in a training room, once this request commits (never
    under its row lock, and never for a request that rolls back). Best effort: tokens carry the same
    rule, so a failure here is corrected the next time anybody joins."""
    if not await is_training(session, circuit.id):
        return
    active = await active_trainee_id(session, org_id, circuit)
    snapshot = SimpleNamespace(open_floor=circuit.open_floor)
    room, circuit_id = floor.room_name_for(circuit.id), str(circuit.id)

    async def apply() -> None:
        """Move everyone's microphone to what the rule now says, once the change is saved."""
        try:
            await agents.set_mic_permissions(
                room, lambda identity: floor.mic_allowed(snapshot, active, identity, training=True)
            )
        except Exception:
            log.warning("could not re-apply microphone permissions", circuit_id=circuit_id, exc_info=True)

    run_after_commit(session, apply)


async def _training_room(session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID) -> Circuit:
    """The locked circuit, if it is a training one whose room is still open (running, or kept after End)."""
    circuit = await _require_circuit(session, org_id, circuit_id, lock=True)
    if not await is_training(session, circuit_id):
        raise errors.NotATrainingCircuit()
    if not floor.room_is_open(
        started=circuit.started_at is not None,
        ended=circuit.ended_at is not None,
        has_room=bool(circuit.room_name),
        closed=circuit.room_closed_at is not None,
        training=True,
    ):
        raise errors.CircuitNotLive()
    return circuit


async def set_floor(
    session: AsyncSession,
    org_id: uuid.UUID,
    circuit_id: uuid.UUID,
    *,
    open_floor: bool,
    agents: RoomAgents,
    actor: Principal,
    now: datetime,
) -> CircuitRead:
    """Unmute or mute everyone (the supervisor and the person with the turn keep theirs)."""
    circuit = await _training_room(session, org_id, circuit_id)
    await repository.update_circuit(session, org_id, circuit_id, open_floor=open_floor)
    circuit.open_floor = open_floor
    await sync_mics(session, org_id, circuit, agents=agents)
    await write_intervention(
        session,
        org_id,
        circuit,
        action=FLOOR_CHANGED,
        actor=Actor(actor.user_id, "Floor opened" if open_floor else "Floor closed"),
        before=circuit.phase_seq,
        now=now,
        clock_moved=False,
    )
    await announcements.circuit_changed(session, org_id, circuit_id, name=announcements.FLOOR_CHANGED)
    return await read_circuit(session, org_id, circuit_id)


def _require_identity_shape(identity: str) -> None:
    """Only a trainee's user id or an observer's `observer-<user id>` reaches the stored label."""
    raw = identity.removeprefix(floor.OBSERVER_PREFIX)
    try:
        uuid.UUID(raw)
    except ValueError:
        raise InvalidInput("That is not a person in this room.") from None


async def set_participant_mic(
    session: AsyncSession,
    org_id: uuid.UUID,
    circuit_id: uuid.UUID,
    *,
    identity: str,
    allowed: bool,
    agents: RoomAgents,
    actor: Principal,
    now: datetime,
) -> CircuitRead:
    """Switch one person's microphone for as long as they stay; a rejoin follows the rule again."""
    circuit = await _training_room(session, org_id, circuit_id)
    if identity.startswith(AGENT_PREFIX):
        # The patient has no microphone setting: it is the room's own participant.
        return await read_circuit(session, org_id, circuit_id)
    _require_identity_shape(identity)
    room = floor.room_name_for(circuit_id)

    async def apply() -> None:
        """Switch the one microphone once the intervention is saved; never under the row lock."""
        try:
            await agents.set_mic_permission(room, identity, allowed)
        except Exception:
            log.warning("could not switch a microphone", circuit_id=str(circuit_id), exc_info=True)

    run_after_commit(session, apply)
    await write_intervention(
        session,
        org_id,
        circuit,
        action=MIC_CHANGED,
        actor=Actor(actor.user_id, f"{identity}: microphone {'on' if allowed else 'off'}"),
        before=circuit.phase_seq,
        now=now,
        clock_moved=False,
    )
    await announcements.circuit_changed(session, org_id, circuit_id, name=announcements.FLOOR_CHANGED)
    return await read_circuit(session, org_id, circuit_id)


async def close_room(
    session: AsyncSession,
    org_id: uuid.UUID,
    circuit_id: uuid.UUID,
    *,
    agents: RoomAgents,
    actor: Principal,
    now: datetime,
) -> CircuitRead:
    """Close the room kept open after End, disconnecting everyone in it."""
    circuit = await _training_room(session, org_id, circuit_id)
    if circuit.ended_at is None:
        raise errors.CircuitNotEnded()
    room = floor.room_name_for(circuit_id)

    async def apply() -> None:
        """Disconnect everyone once the close is saved; never under the row lock."""
        try:
            await agents.close_room(room, force=True)
        except Exception:
            log.warning("could not close the room", circuit_id=str(circuit_id), exc_info=True)

    run_after_commit(session, apply)
    await repository.update_circuit(session, org_id, circuit_id, room_closed_at=now)
    circuit.room_closed_at = now
    await write_intervention(
        session,
        org_id,
        circuit,
        action=ROOM_CLOSED,
        actor=Actor(actor.user_id, "Room closed"),
        before=circuit.phase_seq,
        now=now,
        clock_moved=False,
    )
    await announcements.circuit_changed(session, org_id, circuit_id, name=announcements.ROOM_CLOSED)
    return await read_circuit(session, org_id, circuit_id)
