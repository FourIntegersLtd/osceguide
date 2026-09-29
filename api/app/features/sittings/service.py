"""Scheduling a sitting: creating one, and building the circuits inside it.

Running a circuit is `service_run.py`: this one moves when an examination is
*composed* differently, that one when it is *run* differently.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, raise_mapped
from app.features.catalog import service as catalog
from app.features.roster import service as roster
from app.features.rubrics import service_marking
from app.features.sittings import domain, domain_edit, domain_run, errors, repository
from app.features.sittings.models import Circuit, Sitting, Slot
from app.features.sittings.reads import circuit_read, sitting_read, timing_json
from app.features.sittings.schemas import CircuitRead, SittingRead, TimingIn

# One place mapping a domain refusal to its API code — the running rules
# included, so an override and a structural edit cannot answer differently for
# the same reason.
_REFUSALS: dict[type[Exception], type[AppError]] = {
    domain.InvalidCircuit: errors.InvalidCircuitError,
    domain.CircuitLocked: errors.CircuitLockedError,
    domain.CircuitAlreadyEnded: errors.CircuitAlreadyEndedError,
    domain.NotPermittedInMode: errors.NotPermittedInModeError,
    domain_run.CircuitPaused: errors.CircuitPausedError,
    domain_run.CircuitNotPaused: errors.CircuitNotPausedError,
    domain_edit.SittingLocked: errors.SittingLockedError,
    domain_edit.TraineeAlreadyOnCircuit: errors.TraineeAlreadyOnCircuitError,
    domain_edit.StationNotOnCircuit: errors.StationNotOnCircuitError,
}


async def create_sitting(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    name: str,
    mode: str,
    sitting_type: str,
    scheduled_for: datetime | None,
    programme_id: uuid.UUID,
) -> SittingRead:
    """Schedule a new sitting, marked against its programme's published rubric."""
    rubric_version_id = await rubric_version_for_programme(session, org_id, programme_id)

    sitting = await repository.create_sitting(
        session,
        org_id,
        name=name,
        rubric_version_id=rubric_version_id,
        mode=mode,
        sitting_type=sitting_type,
        scheduled_for=scheduled_for,
        programme_id=programme_id,
    )
    return sitting_read(sitting, [])


async def read_sitting(session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID) -> SittingRead:
    """A sitting with every circuit and slot it has, for a console screen."""
    sitting = await _require_sitting(session, org_id, sitting_id)
    circuits = []
    for circuit in await repository.circuits_for_sitting(session, org_id, sitting_id):
        slots = await repository.slots_for_circuit(session, org_id, circuit.id)
        circuits.append(circuit_read(circuit, slots))
    return sitting_read(sitting, circuits)


async def list_sittings(
    session: AsyncSession, org_id: uuid.UUID, *, limit: int, cursor: dict[str, Any] | None
) -> tuple[list[SittingRead], str | None]:
    """A page of this organisation's sittings, newest first."""
    sittings, next_cursor = await repository.list_sittings(session, org_id, limit=limit, cursor=cursor)
    return [sitting_read(sitting, []) for sitting in sittings], next_cursor


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
    """Build a new circuit inside a sitting: check the roster, build its slots, write it."""
    sitting = await _require_sitting(session, org_id, sitting_id)
    mode = domain.Mode(sitting.mode)
    # R3: a revoked trainee is not scheduled into an examination.
    await roster.ensure_rosterable(session, org_id, trainee_ids)

    try:
        planned = domain.build_slots(
            mode,
            trainee_user_ids=[str(trainee_id) for trainee_id in trainee_ids],
            station_version_ids=[str(station_version_id) for station_version_id in station_version_ids],
        )
    except domain.InvalidCircuit as exc:
        raise_mapped(exc, _REFUSALS)

    resolved_timing = domain.normalise_timing(
        {
            "reading_minutes": timing.reading_minutes,
            "simulation_minutes": timing.simulation_minutes,
            "break_minutes": timing.break_minutes,
            "breaks": [{"after_station": after_station} for after_station in timing.breaks],
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
        session, circuit.id, trainee_ids=trainee_ids, station_version_ids=station_version_ids
    )
    slots = await repository.create_slots(
        session,
        org_id,
        circuit.id,
        planned=[
            (slot.index, uuid.UUID(slot.trainee_user_id), uuid.UUID(slot.station_version_id))
            for slot in planned
        ],
    )
    return circuit_read(circuit, slots)


async def read_circuit(session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID) -> CircuitRead:
    """A circuit and its slots as the API shape a console screen reads."""
    circuit = await _require_circuit(session, org_id, circuit_id)
    slots = await repository.slots_for_circuit(session, org_id, circuit_id)
    return circuit_read(circuit, slots)


async def _require_sitting(session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID) -> Sitting:
    """The sitting, or raise `SittingNotFound` if it does not belong to this organisation."""
    sitting = await repository.sitting_by_id(session, org_id, sitting_id)
    if sitting is None:
        raise errors.SittingNotFound()
    return sitting


async def _require_circuit(
    session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID, *, lock: bool = False
) -> Circuit:
    """Load a circuit, optionally holding it for the rest of the transaction.

    `lock=True` for anything that reads the circuit's state and then writes it
    (C4): start, switch, end. Reads leave it unlocked, so a supervisor console
    polling the state does not queue behind a write.
    """
    fetch = repository.circuit_for_update if lock else repository.circuit_by_id
    circuit = await fetch(session, org_id, circuit_id)
    if circuit is None:
        raise errors.CircuitNotFound()
    return circuit


async def slot_is_in_org(session: AsyncSession, org_id: uuid.UUID, slot_id: uuid.UUID) -> bool:
    """Whether this slot belongs to this organisation.

    Exposed for `reviews`, whose routes are addressed by slot id. A slot id in
    a URL says nothing about who owns it, and taking the org from the path
    while trusting the id is how a review came to be storable against another
    tenant's slot (P4).
    """
    return await repository.slot_by_id(session, org_id, slot_id) is not None


async def slot_and_circuit_for_owner(
    session: AsyncSession, slot_id: uuid.UUID, user_id: uuid.UUID
) -> tuple[Slot, Circuit] | None:
    """The slot and its circuit, if the slot is this signed-in person's own.

    Exposed for `reviews`, whose own read of a slot's review needs the slot's
    org and the circuit's sitting to check the result is released, without
    reaching into this slice's repository directly.
    """
    slot = await repository.slot_by_id_for_user(session, slot_id, user_id)
    if slot is None:
        return None
    circuit = await repository.circuit_by_id(session, slot.org_id, slot.circuit_id)
    if circuit is None:
        return None
    return slot, circuit


async def rubric_version_for_slot(
    session: AsyncSession, org_id: uuid.UUID, slot_id: uuid.UUID
) -> uuid.UUID | None:
    """Which rubric version a slot is marked against (R-1), for `reviews`."""
    return await repository.rubric_version_for_slot(session, org_id, slot_id)


# --- Which rubric version a sitting is marked against.


async def rubric_version_for_programme(
    session: AsyncSession, org_id: uuid.UUID, programme_id: uuid.UUID
) -> uuid.UUID:
    """The published rubric version this programme's exam is marked with."""
    exam_id = await catalog.programme_exam_id(session, org_id, programme_id)
    exam = await catalog.exam_row(session, exam_id)
    if exam.rubric_version_id is None:
        raise errors.ExamRubricNotReady("That programme's exam has no published rubric to mark against yet.")
    await service_marking.published_version(session, org_id, exam.rubric_version_id)
    return exam.rubric_version_id
