"""Running a circuit: the bell, and what it does when it rings.

A real OSCE is not driven by somebody remembering to press a button. The
station starts, the patient is already in the room, the bell goes, everyone
moves. This module is that bell.

Every transition schedules the next one for the moment its phase is due to end,
in the same transaction that writes the phase — so the state and the fact that
a transition is owed land together or not at all (ADR 0006). Each scheduled job
carries the `phase_seq` it was scheduled against and does nothing if that no
longer matches, which is how a human's override beats the clock without a
lease, a claim table or a second lock. The mechanics of one step live in
`service_steps.py`.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import raise_mapped
from app.core.logging import get_logger
from app.core.ports import RoomAgents
from app.core.settings import Settings
from app.features.sittings import announcements, domain, domain_run, errors, repository, service_steps
from app.features.sittings.models import Circuit
from app.features.sittings.reads import position_of, state, timing_domain
from app.features.sittings.schemas import CircuitRead
from app.features.sittings.service import _REFUSALS, _require_circuit, read_circuit
from app.features.voice import service as voice

log = get_logger(__name__)

# Re-exported so the router wires the dependency without importing another
# slice: the service is this slice's public face.
get_room_agents = voice.get_room_agents

# How long a circuit may sit live before the reaper closes it.
STALE_AFTER = timedelta(hours=12)


async def start_circuit(
    session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID, *, now: datetime
) -> CircuitRead:
    """Open the room and start the first station's reading time.

    Starting is the only manual act left in an examination. From here the clock
    carries it: the patient arrives when the consultation begins and leaves
    when it ends, a break counts itself down, and the last station ends the
    circuit.
    """
    circuit = await _require_circuit(session, org_id, circuit_id, lock=True)
    try:
        domain.ensure_startable(state(circuit, has_feedback=False))
    except domain.CircuitAlreadyEnded as exc:
        raise_mapped(exc, _REFUSALS)

    room = f"circuit_{circuit.id}"
    await repository.update_circuit(
        session, org_id, circuit_id, room_name=room, started_at=now, ended_at=None
    )
    await repository.update_slots_for_circuit(session, org_id, circuit_id, room_name=room)
    await repository.set_sitting_status(session, org_id, circuit.sitting_id, status="in_progress")
    circuit.room_name = room

    slots = await repository.slots_for_circuit(session, org_id, circuit_id)
    first = domain_run.next_step(
        domain_run.Position(None, None), slot_count=len(slots), timing=timing_domain(circuit.timing)
    )
    # No agents needed: a circuit always opens on a reading period, so nothing
    # is dispatched here.
    await service_steps.apply_step(
        session, org_id, circuit, slots, first, seq=circuit.phase_seq + 1, agents=None, settings=None, now=now
    )
    await announcements.circuit_changed(session, org_id, circuit_id, name=announcements.STARTED)
    return await read_circuit(session, org_id, circuit_id)


async def advance(
    session: AsyncSession,
    org_id: uuid.UUID,
    circuit_id: uuid.UUID,
    *,
    expected_seq: int | None,
    agents: RoomAgents,
    settings: Settings,
    now: datetime,
    by_human: bool = False,
) -> bool:
    """Move the circuit on one step. Returns whether anything happened.

    `expected_seq` is the whole concurrency design. A scheduled transition
    passes the sequence it was scheduled against; if anybody has paused,
    extended or jumped since, the number has moved on and this does nothing. A
    human passes None, because they *are* the intervention.

    Returning rather than raising for a stale sequence: a job that arrives to
    find its moment gone has not failed, and retrying it would be wrong.
    """
    circuit = await _require_circuit(session, org_id, circuit_id, lock=True)
    if circuit.ended_at is not None:
        return False
    if expected_seq is not None and circuit.phase_seq != expected_seq:
        log.info(
            "skipping a transition that was overtaken",
            circuit_id=str(circuit_id),
            expected_seq=expected_seq,
            actual_seq=circuit.phase_seq,
        )
        return False
    if circuit.paused_at is not None:
        # The clock is deliberately stopped. A human asking anyway is told so;
        # a job simply waits for the resume, which reschedules it.
        if by_human:
            raise errors.CircuitPausedError()
        return False
    if not circuit.auto_advance and not by_human:
        return False

    await _step_forward(session, org_id, circuit, agents=agents, settings=settings, now=now)
    await announcements.circuit_changed(session, org_id, circuit_id, name=announcements.PHASE_ADVANCED)
    return True


async def end_circuit(
    session: AsyncSession,
    org_id: uuid.UUID,
    circuit_id: uuid.UUID,
    *,
    agents: RoomAgents,
    now: datetime,
) -> CircuitRead:
    """Stop the whole examination, wherever it had got to.

    The patient is removed here — previously ending a circuit only nulled the
    room name, leaving the agent stuck in a LiveKit room nobody returned to.
    """
    circuit = await _require_circuit(session, org_id, circuit_id, lock=True)
    if circuit.ended_at is None:
        await service_steps.clear_patient(session, org_id, circuit, agents=agents, now=now)
        await service_steps.finish(session, org_id, circuit, now=now)
        await announcements.circuit_changed(session, org_id, circuit_id, name=announcements.ENDED)
    return await read_circuit(session, org_id, circuit_id)


async def _step_forward(
    session: AsyncSession,
    org_id: uuid.UUID,
    circuit: Circuit,
    *,
    agents: RoomAgents,
    settings: Settings,
    now: datetime,
) -> None:
    """Work out the next step from where the circuit is now, and put it there."""
    slots = await repository.slots_for_circuit(session, org_id, circuit.id)
    step = domain_run.next_step(
        position_of(circuit, slots), slot_count=len(slots), timing=timing_domain(circuit.timing)
    )
    await service_steps.apply_step(
        session,
        org_id,
        circuit,
        slots,
        step,
        seq=circuit.phase_seq + 1,
        agents=agents,
        settings=settings,
        now=now,
    )


async def require_live(session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID) -> Circuit:
    """A circuit that is running: started, not ended, in a room.

    One refusal for "you cannot do that to this circuit", so a client has one
    code to handle rather than three that mean the same thing.
    """
    circuit = await _require_circuit(session, org_id, circuit_id)
    if circuit.started_at is None or circuit.ended_at is not None or not circuit.room_name:
        raise errors.CircuitNotLive()
    return circuit
