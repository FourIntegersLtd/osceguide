"""Mapping sitting rows to their API shapes.

Split from `service.py` at the file cap. The use cases and the projections
change for different reasons: a rule moves because an examination works
differently, a projection moves because a screen needs another field.
"""

from __future__ import annotations

from typing import Any

from app.features.sittings import domain, domain_run
from app.features.sittings.models import Circuit, Sitting, Slot
from app.features.sittings.schemas import CircuitRead, SittingRead, SlotRead, TimingRead


def state(circuit: Circuit, *, has_feedback: bool) -> domain.CircuitState:
    return domain.CircuitState(
        active_slot_id=str(circuit.active_slot_id) if circuit.active_slot_id else None,
        has_feedback=has_feedback,
        ended=circuit.ended_at is not None,
    )


def position_of(circuit: Circuit, slots: list[Slot]) -> domain_run.Position:
    """Where this circuit is, in the run machine's terms.

    The phase is the circuit's; the index is looked up from the active slot,
    because the machine walks positions and the row names a slot.
    """
    phase = domain_run.RunPhase(circuit.phase) if circuit.phase else None
    index: int | None = None
    if circuit.active_slot_id is not None:
        index = next((s.slot_index for s in slots if s.id == circuit.active_slot_id), None)
    if phase is domain_run.RunPhase.BREAK and index is None:
        # A break clears the active slot, so the position is carried by the
        # station it follows: the last one whose consultation completed.
        completed = [s.slot_index for s in slots if s.status == domain.SlotStatus.COMPLETED]
        index = max(completed) if completed else None
    return domain_run.Position(phase=phase, slot_index=index)


def slot_phase(circuit: Circuit, slot: Slot) -> str | None:
    """The phase to show against one slot.

    Derived rather than stored. The clock is the circuit's, and only the slot
    the circuit is actually on is in a phase — everything else is waiting or
    finished. A stored copy per slot is the two-clocks bug D-6 removed.
    """
    if circuit.active_slot_id != slot.id:
        return None
    return circuit.phase


def timing_json(timing: domain.Timing) -> dict[str, Any]:
    return {
        "reading_minutes": timing.reading_minutes,
        "simulation_minutes": timing.simulation_minutes,
        "break_minutes": timing.break_minutes,
        "breaks": [b.after_station for b in timing.breaks],
    }


def timing_read(raw: dict[str, Any] | None) -> TimingRead:
    data = raw or {}
    return TimingRead(
        reading_minutes=int(data.get("reading_minutes", domain.DEFAULT_READING_MINUTES)),
        simulation_minutes=int(data.get("simulation_minutes", domain.DEFAULT_SIMULATION_MINUTES)),
        break_minutes=int(data.get("break_minutes", domain.DEFAULT_BREAK_MINUTES)),
        breaks=list(data.get("breaks") or []),
    )


def timing_domain(raw: dict[str, Any] | None) -> domain.Timing:
    """The circuit's timing as the run machine wants it.

    Read back through `timing_read` so an old row missing `break_minutes` gets
    the same default here as it does on a screen.
    """
    read = timing_read(raw)
    return domain.Timing(
        reading_minutes=read.reading_minutes,
        simulation_minutes=read.simulation_minutes,
        break_minutes=read.break_minutes,
        breaks=tuple(domain.Break(after_station=n) for n in read.breaks),
    )


def slot_read(slot: Slot, circuit: Circuit) -> SlotRead:
    return SlotRead(
        id=slot.id,
        slot_index=slot.slot_index,
        trainee_id=slot.trainee_id,
        station_version_id=slot.station_version_id,
        status=slot.status,
        room_name=slot.room_name,
        started_at=slot.started_at,
        ended_at=slot.ended_at,
        phase=slot_phase(circuit, slot),
        phase_started_at=circuit.phase_started_at if circuit.active_slot_id == slot.id else None,
        phase_ends_at=circuit.phase_ends_at if circuit.active_slot_id == slot.id else None,
    )


def circuit_read(circuit: Circuit, slots: list[Slot]) -> CircuitRead:
    return CircuitRead(
        id=circuit.id,
        sitting_id=circuit.sitting_id,
        name=circuit.name,
        supervisor_user_id=circuit.supervisor_user_id,
        timing=timing_read(circuit.timing),
        active_slot_id=circuit.active_slot_id,
        room_name=circuit.room_name,
        started_at=circuit.started_at,
        ended_at=circuit.ended_at,
        phase=circuit.phase,
        phase_started_at=circuit.phase_started_at,
        phase_ends_at=circuit.phase_ends_at,
        phase_seq=circuit.phase_seq,
        paused=circuit.paused_at is not None,
        paused_at=circuit.paused_at,
        auto_advance=circuit.auto_advance,
        slots=[slot_read(s, circuit) for s in slots],
    )


def sitting_read(sitting: Sitting, circuits: list[CircuitRead]) -> SittingRead:
    return SittingRead(
        id=sitting.id,
        name=sitting.name,
        mode=sitting.mode,
        sitting_type=sitting.sitting_type,
        status=sitting.status,
        scheduled_for=sitting.scheduled_for,
        rubric_version_id=sitting.rubric_version_id,
        programme_id=sitting.programme_id,
        circuits=circuits,
    )
