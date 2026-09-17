"""Sitting and circuit use cases."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, raise_mapped
from app.features.roster import service as roster
from app.features.rubrics import service_feedback as rubrics
from app.features.sittings import announcements, domain, errors, repository
from app.features.sittings.models import Circuit, Sitting
from app.features.sittings.reads import (
    CLEAR_PHASE,
    circuit_read,
    phase_values,
    sitting_read,
    state,
    timing_json,
)
from app.features.sittings.schemas import (
    CircuitRead,
    SittingRead,
    TimingIn,
)

# One place mapping a domain refusal to its API code.
_REFUSALS: dict[type[Exception], type[AppError]] = {
    domain.InvalidCircuit: errors.InvalidCircuitError,
    domain.CircuitLocked: errors.CircuitLockedError,
    domain.CircuitAlreadyEnded: errors.CircuitAlreadyEndedError,
    domain.NotPermittedInMode: errors.NotPermittedInModeError,
}


async def create_sitting(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    name: str,
    feedback_template_version_id: uuid.UUID,
    mode: str,
    sitting_type: str,
    scheduled_for: datetime | None,
    programme_id: uuid.UUID | None,
) -> SittingRead:
    # S1: the rubric must exist, belong to this org, and be published. The
    # NOT NULL foreign key only guarantees the first of those.
    await rubrics.published_feedback_template(session, org_id, feedback_template_version_id)

    row = await repository.create_sitting(
        session,
        org_id,
        name=name,
        feedback_template_version_id=feedback_template_version_id,
        mode=mode,
        sitting_type=sitting_type,
        scheduled_for=scheduled_for,
        programme_id=programme_id,
    )
    return sitting_read(row, [])


async def read_sitting(session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID) -> SittingRead:
    sitting = await _require_sitting(session, org_id, sitting_id)
    circuits = []
    for circuit in await repository.circuits_for_sitting(session, org_id, sitting_id):
        slots = await repository.slots_for_circuit(session, org_id, circuit.id)
        circuits.append(circuit_read(circuit, slots))
    return sitting_read(sitting, circuits)


async def list_sittings(
    session: AsyncSession, org_id: uuid.UUID, *, limit: int, cursor: dict[str, Any] | None
) -> tuple[list[SittingRead], str | None]:
    rows, next_cursor = await repository.list_sittings(session, org_id, limit=limit, cursor=cursor)
    return [sitting_read(r, []) for r in rows], next_cursor


async def add_circuit(
    session: AsyncSession,
    org_id: uuid.UUID,
    sitting_id: uuid.UUID,
    *,
    name: str,
    trainee_ids: list[uuid.UUID],
    station_version_ids: list[uuid.UUID],
    supervisor_user_id: uuid.UUID | None,
    timing: TimingIn,
) -> CircuitRead:
    sitting = await _require_sitting(session, org_id, sitting_id)
    mode = domain.Mode(sitting.mode)
    # R3: a revoked trainee is not scheduled into an examination.
    await roster.ensure_rosterable(session, org_id, trainee_ids)

    try:
        planned = domain.build_slots(
            mode,
            trainees=[str(t) for t in trainee_ids],
            stations=[str(s) for s in station_version_ids],
        )
    except domain.InvalidCircuit as exc:
        raise_mapped(exc, _REFUSALS)

    resolved_timing = domain.normalise_timing(
        {
            "reading_minutes": timing.reading_minutes,
            "simulation_minutes": timing.simulation_minutes,
            "breaks": [{"after_station": b} for b in timing.breaks],
        },
        mode=mode,
        station_count=len(station_version_ids),
    )

    circuit = await repository.create_circuit(
        session,
        org_id,
        sitting_id=sitting_id,
        name=name,
        supervisor_user_id=supervisor_user_id,
        timing=timing_json(resolved_timing),
    )
    await repository.add_circuit_members(
        session, circuit.id, trainees=trainee_ids, stations=station_version_ids
    )
    slots = await repository.create_slots(
        session,
        org_id,
        circuit.id,
        planned=[(p.index, uuid.UUID(p.trainee), uuid.UUID(p.station)) for p in planned],
    )
    return circuit_read(circuit, slots)


async def start_circuit(
    session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID, *, now: datetime
) -> CircuitRead:
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
    await announcements.circuit_changed(session, org_id, circuit_id, name=announcements.STARTED)
    return await read_circuit(session, org_id, circuit_id)


async def switch_turn(
    session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID, *, slot_id: uuid.UUID, now: datetime
) -> CircuitRead:
    circuit = await _require_circuit(session, org_id, circuit_id, lock=True)
    sitting = await _require_sitting(session, org_id, circuit.sitting_id)
    try:
        # Order matters: the circuit being over is the more fundamental
        # refusal, and it is the one a racing `end_circuit` creates.
        domain.ensure_live(state(circuit, has_feedback=False))
        domain.ensure_can_switch_turn(domain.Mode(sitting.mode))
    except (domain.CircuitAlreadyEnded, domain.NotPermittedInMode) as exc:
        raise_mapped(exc, _REFUSALS)

    slot = await repository.slot_by_id(session, org_id, slot_id)
    if slot is None or slot.circuit_id != circuit_id:
        raise errors.SlotNotFound()
    # Moving the turn starts the new candidate's reading time on the server
    # (D-6), and takes the clock off whoever held it before.
    if circuit.active_slot_id is not None and circuit.active_slot_id != slot_id:
        await repository.update_slot(session, org_id, circuit.active_slot_id, **CLEAR_PHASE)
    await repository.update_slot(session, org_id, slot_id, **phase_values(domain.Phase.READING, circuit, now))
    await repository.update_circuit(session, org_id, circuit_id, active_slot_id=slot_id)
    await announcements.circuit_changed(session, org_id, circuit_id, name=announcements.TURN_SWITCHED)
    return await read_circuit(session, org_id, circuit_id)


async def end_circuit(
    session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID, *, now: datetime
) -> CircuitRead:
    await _require_circuit(session, org_id, circuit_id, lock=True)
    await repository.update_circuit(
        session,
        org_id,
        circuit_id,
        ended_at=now,
        active_slot_id=None,
        agent_dispatched_at=None,
        room_name=None,
    )
    # Clearing the room on every slot is what tells a rejoining browser the
    # circuit is over; b2b does the same on end. The clocks go with it.
    await repository.update_slots_for_circuit(session, org_id, circuit_id, room_name=None, **CLEAR_PHASE)
    await announcements.circuit_changed(session, org_id, circuit_id, name=announcements.ENDED)
    return await read_circuit(session, org_id, circuit_id)


async def read_circuit(session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID) -> CircuitRead:
    circuit = await _require_circuit(session, org_id, circuit_id)
    slots = await repository.slots_for_circuit(session, org_id, circuit_id)
    return circuit_read(circuit, slots)


async def _require_sitting(session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID) -> Sitting:
    row = await repository.sitting_by_id(session, org_id, sitting_id)
    if row is None:
        raise errors.SittingNotFound()
    return row


async def _require_circuit(
    session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID, *, lock: bool = False
) -> Circuit:
    """Load a circuit, optionally holding it for the rest of the transaction.

    `lock=True` for anything that reads the circuit's state and then writes it
    (C4): start, switch, end. Reads leave it unlocked, so a supervisor console
    polling the state does not queue behind a write.
    """
    fetch = repository.circuit_for_update if lock else repository.circuit_by_id
    row = await fetch(session, org_id, circuit_id)
    if row is None:
        raise errors.CircuitNotFound()
    return row


async def slot_is_in_org(session: AsyncSession, org_id: uuid.UUID, slot_id: uuid.UUID) -> bool:
    """Whether this slot belongs to this organisation.

    Exposed for `reviews`, whose routes are addressed by slot id. A slot id in
    a URL says nothing about who owns it, and taking the org from the path
    while trusting the id is how a review came to be storable against another
    tenant's slot (P4).
    """
    return await repository.slot_by_id(session, org_id, slot_id) is not None


async def feedback_template_version_for_slot(
    session: AsyncSession, org_id: uuid.UUID, slot_id: uuid.UUID
) -> uuid.UUID | None:
    """Which rubric a slot is marked against (R-1), for `reviews`."""
    return await repository.feedback_template_version_for_slot(session, org_id, slot_id)
