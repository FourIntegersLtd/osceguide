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

from app.core.auth import Principal
from app.core.db import savepoint
from app.core.errors import raise_mapped
from app.core.logging import get_logger
from app.core.ports import RoomAgents
from app.core.settings import Settings
from app.core.tenancy import OrgSuspended
from app.features.sittings import (
    announcements,
    domain,
    domain_run,
    errors,
    repository,
    service_steps,
)
from app.features.sittings.models import Circuit
from app.features.sittings.overrides import AUTO_END, Actor, write_intervention
from app.features.sittings.reads import position_of, state, timing_domain
from app.features.sittings.schemas import CircuitRead
from app.features.sittings.service import (
    _REFUSALS,
    _require_circuit,
    _require_sitting,
    ensure_lead_may_run,
    ensure_sitting_not_cancelled,
    ensure_sitting_programme_active,
    read_circuit,
)
from app.features.tenancy import service as tenancy
from app.features.tenancy import service_audit as tenancy_audit
from app.features.voice import service as voice
from app.features.voice.errors import VoiceUnavailable

log = get_logger(__name__)

# Re-exported so the router wires the dependency without importing another
# slice: the service is this slice's public face.
get_room_agents = voice.get_room_agents

# How long a running circuit's clock may sit with nothing to count before the reaper closes it.
STALE_AFTER = timedelta(hours=12)
_AUTO_END_REASON = (
    f"Ended automatically: the clock had nothing to count for {STALE_AFTER.total_seconds() / 3600:g} hours"
)


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
    current = state(circuit, has_feedback=False)
    try:
        domain.ensure_startable(current)
    except domain.CircuitAlreadyEnded as exc:
        raise_mapped(exc, _REFUSALS)
    if current.started:
        return await read_circuit(session, org_id, circuit_id)
    sitting = await _require_sitting(session, org_id, circuit.sitting_id)
    ensure_sitting_not_cancelled(sitting)
    await ensure_sitting_programme_active(session, org_id, sitting)
    # S-17: nothing new starts for a suspended organisation, whoever asks.
    org = await tenancy.org_ref_by_id(session, org_id)
    if org is None or not tenancy.org_permits_access(org.status):
        raise OrgSuspended()
    # R-41: a lead who lost the role since the circuit was built cannot run it.
    await ensure_lead_may_run(session, org_id, circuit.supervisor_user_id)

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

    if by_human:
        await _step_forward(session, org_id, circuit, agents=agents, settings=settings, now=now)
    else:
        try:
            async with savepoint(session):
                await _step_forward(session, org_id, circuit, agents=agents, settings=settings, now=now)
        except VoiceUnavailable:
            # R-16: the circuit stays where it was for the next try, and says why, so the
            # board can tell a voice fault from a worker that is not running.
            await repository.update_circuit(session, org_id, circuit_id, voice_fault_at=now)
            circuit.voice_fault_at = now
            log.warning("voice unavailable; circuit left for the next try", circuit_id=str(circuit_id))
            return False
    if circuit.voice_fault_at is not None:
        await repository.update_circuit(session, org_id, circuit_id, voice_fault_at=None)
        circuit.voice_fault_at = None
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
    """Stop the whole examination, wherever it had got to, without an audit row: the reaper's
    end, which writes its own intervention. A person pressing End goes through `end_circuit_by`.

    The patient is removed here — previously ending a circuit only nulled the
    room name, leaving the agent stuck in a LiveKit room nobody returned to.
    With LiveKit down the end still lands, and the removal is owed as a
    retried job rather than dropped (R-13).
    """
    circuit = await _require_circuit(session, org_id, circuit_id, lock=True)
    await _end_if_open(session, org_id, circuit, agents=agents, now=now)
    return await read_circuit(session, org_id, circuit_id)


async def _end_if_open(
    session: AsyncSession, org_id: uuid.UUID, circuit: Circuit, *, agents: RoomAgents, now: datetime
) -> bool:
    """End a loaded, locked circuit if it is still running; whether this call ended it."""
    if circuit.ended_at is not None:
        return False
    if not await service_steps.clear_patient(
        session, org_id, circuit, agents=agents, now=now, station_sat=True
    ):
        await service_steps.clear_patient_later(session, circuit)
    await service_steps.finish(session, org_id, circuit, now=now)
    await announcements.circuit_changed(session, org_id, circuit.id, name=announcements.ENDED)
    return True


async def end_circuit_by(
    session: AsyncSession,
    org_id: uuid.UUID,
    circuit_id: uuid.UUID,
    *,
    agents: RoomAgents,
    now: datetime,
    actor: Principal,
    reason: str | None = None,
) -> CircuitRead:
    """A person ends the circuit: `end_circuit`, plus the audit row (none if it had already ended)."""
    circuit = await _require_circuit(session, org_id, circuit_id, lock=True)
    if await _end_if_open(session, org_id, circuit, agents=agents, now=now):
        await tenancy_audit.record_for_owner(
            session,
            org_id=org_id,
            actor=actor,
            action="circuit.ended",
            target_type="circuit",
            target_id=str(circuit_id),
            summary=f"Circuit {circuit.name} ended by hand"
            + (f": {reason.strip()}" if reason and reason.strip() else ""),
        )
    return await read_circuit(session, org_id, circuit_id)


async def end_abandoned(
    session: AsyncSession,
    org_id: uuid.UUID,
    circuit_id: uuid.UUID,
    *,
    agents: RoomAgents,
    now: datetime,
) -> CircuitRead:
    """The reaper's end: the same as a human's, plus a record saying nobody pressed it (R-15).

    Without the record the console's history shows a circuit that simply
    stopped, and the supervisor has no way to tell a crash from the reaper.
    """
    circuit = await _require_circuit(session, org_id, circuit_id, lock=True)
    if circuit.ended_at is None:
        await write_intervention(
            session,
            org_id,
            circuit,
            action=AUTO_END,
            actor=Actor(user_id=None, reason=_AUTO_END_REASON),
            before=circuit.phase_seq,
            now=now,
        )
    return await end_circuit(session, org_id, circuit_id, agents=agents, now=now)


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
        position_of(circuit, slots),
        slot_count=len(slots),
        timing=timing_domain(circuit.timing),
        done={slot.slot_index for slot in slots if slot.status in domain.FINISHED_SLOT_STATUSES},
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
