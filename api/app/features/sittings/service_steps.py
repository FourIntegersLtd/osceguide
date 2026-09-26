"""What one step of a circuit does to the database.

Given a step the run machine chose, put the circuit into it: move the
patient, close off the station that ended, write the clock, and owe the next
transition.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ports import RoomAgents
from app.core.settings import Settings
from app.features.sittings import domain, domain_run, errors, repository, repository_run
from app.features.sittings.models import Circuit, Slot

# Re-exported: `service_steps` is the whole step layer as far as its callers
# are concerned, and which file a step's body lives in is not their business.
from app.features.sittings.service_clock import schedule_next as schedule_next
from app.features.sittings.service_clock import set_phase
from app.features.sittings.service_patient import clear_patient as clear_patient
from app.features.sittings.service_patient import dispatch_patient as dispatch_patient

# Larger than any circuit: an exam circuit is capped at twelve stations and a
# training circuit takes one per trainee.
_ALL_SLOTS = 1_000_000

# The statuses that mean a station has not been sat yet, and so can still be
# closed off as skipped when the circuit moves past it.
_UNSAT = (domain.SlotStatus.SCHEDULED, domain.SlotStatus.READING, domain.SlotStatus.IN_CONSULTATION)


async def apply_step(
    session: AsyncSession,
    org_id: uuid.UUID,
    circuit: Circuit,
    slots: list[Slot],
    step: domain_run.Step,
    *,
    seq: int,
    agents: RoomAgents | None,
    settings: Settings | None,
    now: datetime,
) -> None:
    """Put the circuit into `step`, having left whatever it was in.

    Leaving a consultation is what ends a recording: removing the agent is the
    signal the worker treats as the end of the conversation, and it posts the
    full transcript on its way out. So the order matters — the patient leaves
    before the next station's clock starts, never after.
    """
    if circuit.phase == domain_run.RunPhase.SIMULATION and agents is not None:
        await clear_patient(session, org_id, circuit, agents=agents, now=now)

    match step:
        case domain_run.Reading(slot_index=index):
            await begin_reading(session, org_id, circuit, slots, index, seq=seq, now=now)
        case domain_run.Simulation(slot_index=index):
            await begin_consultation(
                session, org_id, circuit, slots, index, seq=seq, agents=agents, settings=settings, now=now
            )
        case domain_run.BreakStep(after_station=after):
            await begin_break(session, org_id, circuit, after, seq=seq, now=now)
        case _:
            await finish(session, org_id, circuit, now=now)


async def begin_reading(
    session: AsyncSession,
    org_id: uuid.UUID,
    circuit: Circuit,
    slots: list[Slot],
    index: int,
    *,
    seq: int,
    now: datetime,
) -> None:
    slot = slot_at(slots, index)
    await repository.update_slot(
        session,
        org_id,
        slot.id,
        status=domain.SlotStatus.READING,
        # Kept if the station is being redone: `started_at` is when the
        # candidate first saw it, which a retry does not change.
        started_at=slot.started_at or now,
        ended_at=None,
    )
    await set_phase(
        session, org_id, circuit, domain_run.Reading(index), seq=seq, now=now, active_slot_id=slot.id
    )


async def begin_consultation(
    session: AsyncSession,
    org_id: uuid.UUID,
    circuit: Circuit,
    slots: list[Slot],
    index: int,
    *,
    seq: int,
    agents: RoomAgents | None,
    settings: Settings | None,
    now: datetime,
) -> None:
    slot = slot_at(slots, index)
    if agents is None or settings is None:
        raise RuntimeError("A consultation cannot start without a way to put the patient in the room.")
    await dispatch_patient(session, org_id, circuit, slot, agents=agents, settings=settings, now=now)
    await repository.update_slot(session, org_id, slot.id, status=domain.SlotStatus.IN_CONSULTATION)
    await set_phase(
        session,
        org_id,
        circuit,
        domain_run.Simulation(index),
        seq=seq,
        now=now,
        active_slot_id=slot.id,
        agent_dispatched_at=now,
    )


async def begin_break(
    session: AsyncSession,
    org_id: uuid.UUID,
    circuit: Circuit,
    after_station: int,
    *,
    seq: int,
    now: datetime,
) -> None:
    """A break belongs to no slot, which is the reason the clock is the circuit's."""
    await set_phase(
        session,
        org_id,
        circuit,
        domain_run.BreakStep(after_station),
        seq=seq,
        now=now,
        active_slot_id=None,
        agent_dispatched_at=None,
    )


async def finish(session: AsyncSession, org_id: uuid.UUID, circuit: Circuit, *, now: datetime) -> None:
    """Close the circuit, and with it the room, the clock and every open slot."""
    seq = circuit.phase_seq + 1
    await repository.update_circuit(
        session,
        org_id,
        circuit.id,
        ended_at=now,
        active_slot_id=None,
        agent_dispatched_at=None,
        room_name=None,
        phase=None,
        phase_started_at=None,
        phase_ends_at=None,
        # Bumped so any transition still in the queue arrives holding a number
        # that no longer matches, and does nothing.
        phase_seq=seq,
        paused_at=None,
    )
    # Clearing the room on every slot is what tells a rejoining browser that
    # the circuit is over.
    await repository.update_slots_for_circuit(session, org_id, circuit.id, room_name=None)
    # A station nobody sat is `skipped`, not left looking scheduled: it is not
    # coming.
    await repository_run.mark_slots_skipped(
        session, org_id, circuit.id, before_index=_ALL_SLOTS, statuses=_UNSAT
    )
    circuit.ended_at = now
    circuit.phase = None
    circuit.phase_seq = seq
    await _close_sitting_if_over(session, org_id, circuit)


async def _close_sitting_if_over(session: AsyncSession, org_id: uuid.UUID, circuit: Circuit) -> None:
    """The last circuit to end closes its sitting (D-7).

    Without this, `start_circuit` sets the sitting `in_progress` and nothing
    ever moves it again, so a finished exam day reads as running forever.
    Checked here because every way a circuit can end goes through `finish`.
    """
    siblings = await repository.circuits_for_sitting(session, org_id, circuit.sitting_id)
    ended = [(sibling.ended_at is not None or sibling.id == circuit.id) for sibling in siblings]
    if domain_run.sitting_is_over(ended):
        await repository.set_sitting_status(session, org_id, circuit.sitting_id, status="completed")


def slot_at(slots: list[Slot], index: int) -> Slot:
    found = next((slot for slot in slots if slot.slot_index == index), None)
    if found is None:
        raise errors.SlotNotFound()
    return found
