"""Mapping sitting rows to their API shapes.

Split from `service.py` at the file cap. The use cases and the projections
change for different reasons: a rule moves because an examination works
differently, a projection moves because a screen needs another field.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.features.sittings import domain
from app.features.sittings.models import Circuit, Sitting, Slot
from app.features.sittings.schemas import CircuitRead, SittingRead, SlotRead, TimingRead


def state(circuit: Circuit, *, has_feedback: bool) -> domain.CircuitState:
    return domain.CircuitState(
        active_slot_id=str(circuit.active_slot_id) if circuit.active_slot_id else None,
        has_feedback=has_feedback,
        ended=circuit.ended_at is not None,
    )


CLEAR_PHASE: dict[str, Any] = {"phase": None, "phase_started_at": None, "phase_ends_at": None}


def phase_values(phase: domain.Phase, circuit: Circuit, now: datetime) -> dict[str, Any]:
    """The slot columns that put `phase` on the server clock from `now`."""
    timing = timing_read(circuit.timing)
    started, ends = domain.phase_window(
        phase, reading_minutes=timing.reading_minutes, simulation_minutes=timing.simulation_minutes, now=now
    )
    return {"phase": str(phase), "phase_started_at": started, "phase_ends_at": ends}


def timing_json(timing: domain.Timing) -> dict[str, Any]:
    return {
        "reading_minutes": timing.reading_minutes,
        "simulation_minutes": timing.simulation_minutes,
        "breaks": [b.after_station for b in timing.breaks],
    }


def timing_read(raw: dict[str, Any] | None) -> TimingRead:
    data = raw or {}
    return TimingRead(
        reading_minutes=int(data.get("reading_minutes", domain.DEFAULT_READING_MINUTES)),
        simulation_minutes=int(data.get("simulation_minutes", domain.DEFAULT_SIMULATION_MINUTES)),
        breaks=list(data.get("breaks") or []),
    )


def slot_read(slot: Slot) -> SlotRead:
    return SlotRead(
        id=slot.id,
        slot_index=slot.slot_index,
        trainee_id=slot.trainee_id,
        station_version_id=slot.station_version_id,
        status=slot.status,
        room_name=slot.room_name,
        started_at=slot.started_at,
        ended_at=slot.ended_at,
        phase=slot.phase,
        phase_started_at=slot.phase_started_at,
        phase_ends_at=slot.phase_ends_at,
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
        slots=[slot_read(s) for s in slots],
    )


def sitting_read(sitting: Sitting, circuits: list[CircuitRead]) -> SittingRead:
    return SittingRead(
        id=sitting.id,
        name=sitting.name,
        mode=sitting.mode,
        sitting_type=sitting.sitting_type,
        status=sitting.status,
        scheduled_for=sitting.scheduled_for,
        feedback_template_version_id=sitting.feedback_template_version_id,
        circuits=circuits,
    )
