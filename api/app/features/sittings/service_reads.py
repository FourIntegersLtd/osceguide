"""The queries `dashboard` asks of this slice, filling the shapes next door.

Split from `reads_types.py` at the file cap, at the seam that was already
there: the dataclasses are the contract another slice reads, and these are the
queries that fill them.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.sittings import (
    domain,
    domain_alerts,
    domain_run,
    repository,
    repository_reads,
    repository_run,
)
from app.features.sittings.models import Circuit, Sitting, Slot
from app.features.sittings.reads import timing_read

# Re-exported: a caller asks this module for a circuit and is handed a
# `CircuitRef`, so it should not have to know which file the dataclass is in.
from app.features.sittings.reads_types import CircuitDetail as CircuitDetail
from app.features.sittings.reads_types import CircuitRef as CircuitRef
from app.features.sittings.reads_types import SittingDetail as SittingDetail
from app.features.sittings.reads_types import SittingRef as SittingRef
from app.features.sittings.reads_types import SlotRef as SlotRef
from app.features.sittings.reads_types import SupervisorCircuit as SupervisorCircuit
from app.features.sittings.reads_types import TraineeSlot as TraineeSlot


def _sitting_ref(row: Sitting) -> SittingRef:
    return SittingRef(
        id=row.id,
        org_id=row.org_id,
        name=row.name,
        mode=row.mode,
        sitting_type=row.sitting_type,
        status=row.status,
        scheduled_for=row.scheduled_for,
        rubric_version_id=row.rubric_version_id,
        programme_id=row.programme_id,
    )


def _circuit_ref(row: Circuit) -> CircuitRef:
    return CircuitRef(
        id=row.id,
        sitting_id=row.sitting_id,
        name=row.name,
        supervisor_user_id=row.supervisor_user_id,
        timing=timing_read(row.timing),
        active_slot_id=row.active_slot_id,
        room_name=row.room_name,
        agent_dispatched_at=row.agent_dispatched_at,
        started_at=row.started_at,
        ended_at=row.ended_at,
        phase=row.phase,
        phase_started_at=row.phase_started_at,
        phase_ends_at=row.phase_ends_at,
        phase_seq=row.phase_seq,
        paused_at=row.paused_at,
        paused_seconds=row.paused_seconds,
        auto_advance=row.auto_advance,
    )


def _slot_ref(row: Slot) -> SlotRef:
    return SlotRef(
        id=row.id,
        circuit_id=row.circuit_id,
        slot_index=row.slot_index,
        trainee_id=row.trainee_id,
        station_version_id=row.station_version_id,
        status=row.status,
        room_name=row.room_name,
        started_at=row.started_at,
        ended_at=row.ended_at,
        exam_completed_at=row.exam_completed_at,
    )


async def count_sittings(session: AsyncSession, org_id: uuid.UUID) -> int:
    return await repository_reads.count_sittings(session, org_id)


async def recent_sittings(session: AsyncSession, org_id: uuid.UUID, *, limit: int) -> list[SittingRef]:
    rows, _ = await repository.list_sittings(session, org_id, limit=limit, cursor=None)
    return [_sitting_ref(row) for row in rows]


async def supervisor_circuits(
    session: AsyncSession, org_id: uuid.UUID, supervisor_user_id: uuid.UUID
) -> list[SupervisorCircuit]:
    pairs = await repository_reads.circuits_for_supervisor(session, org_id, supervisor_user_id)
    counts = await repository_reads.slot_counts_for_circuits(session, org_id, [c.id for c, _ in pairs])
    return [
        SupervisorCircuit(
            circuit=_circuit_ref(circuit),
            sitting=_sitting_ref(sitting),
            slot_count=counts.get(circuit.id, 0),
        )
        for circuit, sitting in pairs
    ]


async def circuit_detail(
    session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID
) -> CircuitDetail | None:
    """The circuit, its sitting and its slots, or None if it is not this org's."""
    circuit = await repository.circuit_by_id(session, org_id, circuit_id)
    if circuit is None:
        return None
    sitting = await repository.sitting_by_id(session, org_id, circuit.sitting_id)
    if sitting is None:
        return None
    slots = await repository.slots_for_circuit(session, org_id, circuit_id)
    return CircuitDetail(
        circuit=_circuit_ref(circuit),
        sitting=_sitting_ref(sitting),
        slots=[_slot_ref(row) for row in slots],
    )


async def slots_for_trainee(session: AsyncSession, trainee_user_id: uuid.UUID) -> list[TraineeSlot]:
    """Everything this person is rostered onto, in every organisation."""
    rows = await repository_reads.slots_with_context_for_trainee(session, trainee_user_id)
    return [
        TraineeSlot(slot=_slot_ref(slot), circuit=_circuit_ref(circuit), sitting=_sitting_ref(sitting))
        for slot, circuit, sitting in rows
    ]


async def sitting_detail(
    session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID
) -> SittingDetail | None:
    sitting = await repository.sitting_by_id(session, org_id, sitting_id)
    if sitting is None:
        return None
    circuits = []
    for circuit in await repository.circuits_for_sitting(session, org_id, sitting_id):
        slots = await repository.slots_for_circuit(session, org_id, circuit.id)
        circuits.append(
            CircuitDetail(
                circuit=_circuit_ref(circuit),
                sitting=_sitting_ref(sitting),
                slots=[_slot_ref(s) for s in slots],
            )
        )
    return SittingDetail(sitting=_sitting_ref(sitting), circuits=circuits)


async def sitting_ref(session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID) -> SittingRef | None:
    row = await repository.sitting_by_id(session, org_id, sitting_id)
    return None if row is None else _sitting_ref(row)


async def supervisor_for_slot(
    session: AsyncSession, org_id: uuid.UUID, slot_id: uuid.UUID
) -> uuid.UUID | None:
    """Whoever is named to supervise the circuit this slot is being run in.

    Bound into `attempts` by `composition.py`, because that slice sits below this
    one and cannot ask the question of the tables itself — and the question is
    the whole of an examiner's authority to read a candidate's transcript: not
    the role, and not the organisation, but being the named person on this
    circuit. The same thing `observer_token` hands out a room for.
    """
    return await repository_reads.circuit_supervisor_for_slot(session, org_id, slot_id)


async def slots_for_sitting(session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID) -> list[SlotRef]:
    """Every slot in the sitting, across all of its circuits.

    For the cohort summary, which compares candidates within a sitting rather
    than within a circuit — an exam circuit is one candidate, so a per-circuit
    cohort would be a cohort of one.
    """
    return [_slot_ref(row) for row in await repository_reads.slots_for_sitting(session, org_id, sitting_id)]


async def live_circuits(session: AsyncSession, org_id: uuid.UUID) -> list[CircuitDetail]:
    """Every circuit this organisation currently has running, with its slots.

    The exam-day board's question. Asked of this slice rather than answered by
    reading its tables, so the tenant scoping stays in one place.
    """
    details = []
    for circuit, sitting in await repository_run.live_circuits_for_org(session, org_id):
        slots = await repository.slots_for_circuit(session, org_id, circuit.id)
        details.append(
            CircuitDetail(
                circuit=_circuit_ref(circuit),
                sitting=_sitting_ref(sitting),
                slots=[_slot_ref(s) for s in slots],
            )
        )
    return details


# The clock arithmetic and the alerts, re-exported so `dashboard` can compute a
# board without importing this slice's domain: a slice reaches another through
# its service, and these are part of what this one knows.
alerts_for = domain_alerts.alerts_for
elapsed_seconds = domain_run.elapsed_seconds
remaining_seconds = domain_run.remaining_seconds
FINISHED_SLOT_STATUSES = frozenset(str(s) for s in domain.FINISHED_SLOT_STATUSES)
