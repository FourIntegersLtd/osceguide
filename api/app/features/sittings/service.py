"""Scheduling a sitting: creating one, and building the circuits inside it.

Running a circuit is `service_run.py`. The two were one module, and they change
for different reasons: this one moves when an examination is *composed*
differently, that one when it is *run* differently.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, raise_mapped
from app.features.roster import service as roster
from app.features.sittings import domain, domain_run, errors, repository, service_binding
from app.features.sittings.models import Circuit, Sitting
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
    rubric_version_id = await service_binding.rubric_version_for_programme(session, org_id, programme_id)

    row = await repository.create_sitting(
        session,
        org_id,
        name=name,
        rubric_version_id=rubric_version_id,
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
            "break_minutes": timing.break_minutes,
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


async def rubric_version_for_slot(
    session: AsyncSession, org_id: uuid.UUID, slot_id: uuid.UUID
) -> uuid.UUID | None:
    """Which rubric version a slot is marked against (R-1), for `reviews`."""
    return await repository.rubric_version_for_slot(session, org_id, slot_id)
