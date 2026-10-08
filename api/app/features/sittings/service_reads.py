"""The queries `dashboard` asks of this slice, filling the shapes in `reads_types.py`.

The dataclasses there are the contract another slice reads; these are the
queries that fill them.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

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
from app.features.sittings.reads_types import CircuitRun as CircuitRun
from app.features.sittings.reads_types import SittingDetail as SittingDetail
from app.features.sittings.reads_types import SittingRef as SittingRef
from app.features.sittings.reads_types import SlotRef as SlotRef
from app.features.sittings.reads_types import SupervisorCircuit as SupervisorCircuit
from app.features.sittings.reads_types import TraineeSlot as TraineeSlot


def _sitting_ref(sitting: Sitting) -> SittingRef:
    """A sitting row, mapped to the shape another slice reads."""
    return SittingRef(
        id=sitting.id,
        org_id=sitting.org_id,
        name=sitting.name,
        mode=sitting.mode,
        sitting_type=sitting.sitting_type,
        status=sitting.status,
        scheduled_for=sitting.scheduled_for,
        rubric_version_id=sitting.rubric_version_id,
        programme_id=sitting.programme_id,
    )


def _circuit_ref(circuit: Circuit) -> CircuitRef:
    """A circuit row, mapped to the shape another slice reads."""
    return CircuitRef(
        id=circuit.id,
        sitting_id=circuit.sitting_id,
        name=circuit.name,
        supervisor_user_id=circuit.supervisor_user_id,
        timing=timing_read(circuit.timing),
        active_slot_id=circuit.active_slot_id,
        room_name=circuit.room_name,
        agent_dispatched_at=circuit.agent_dispatched_at,
        started_at=circuit.started_at,
        ended_at=circuit.ended_at,
        phase=circuit.phase,
        phase_started_at=circuit.phase_started_at,
        phase_ends_at=circuit.phase_ends_at,
        phase_seq=circuit.phase_seq,
        paused_at=circuit.paused_at,
        paused_seconds=circuit.paused_seconds,
        auto_advance=circuit.auto_advance,
        voice_fault_at=circuit.voice_fault_at,
    )


def _slot_ref(slot: Slot) -> SlotRef:
    """A slot row, mapped to the shape another slice reads."""
    return SlotRef(
        id=slot.id,
        circuit_id=slot.circuit_id,
        slot_index=slot.slot_index,
        trainee_id=slot.trainee_id,
        station_version_id=slot.station_version_id,
        status=slot.status,
        room_name=slot.room_name,
        started_at=slot.started_at,
        ended_at=slot.ended_at,
        exam_completed_at=slot.exam_completed_at,
    )


async def circuits_led_counts(
    session: AsyncSession, org_id: uuid.UUID, user_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """Circuits each of these people supervises, for the team screen."""
    return await repository_reads.circuits_led_counts(session, org_id, user_ids)


async def trainee_activity(
    session: AsyncSession, org_id: uuid.UUID, user_ids: Sequence[uuid.UUID]
) -> tuple[dict[uuid.UUID, int], dict[uuid.UUID, set[uuid.UUID]]]:
    """Per trainee user: stations sat, and programme ids of their sittings, for the roster."""
    return await repository_reads.trainee_activity(session, org_id, user_ids)


async def sitting_counts_by_cohort(
    session: AsyncSession, org_id: uuid.UUID, cohort_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """Sittings held for each cohort, so deleting one can say how many it detaches."""
    return await repository_reads.sitting_counts_by_cohort(session, org_id, cohort_ids)


async def programme_activity(session: AsyncSession, org_id: uuid.UUID) -> dict[uuid.UUID, tuple[int, int]]:
    """Per programme id: (sittings, distinct candidates), for the reporting screen."""
    return await repository_reads.programme_activity(session, org_id)


async def sitting_programmes(session: AsyncSession, org_id: uuid.UUID) -> dict[uuid.UUID, uuid.UUID]:
    """Sitting id to programme id, for rolling a per-sitting figure up to its programme."""
    return await repository_reads.sitting_programmes(session, org_id)


async def count_sittings(session: AsyncSession, org_id: uuid.UUID) -> int:
    return await repository_reads.count_sittings(session, org_id)


async def recent_sittings(session: AsyncSession, org_id: uuid.UUID, *, limit: int) -> list[SittingRef]:
    """This organisation's most recently created sittings."""
    sittings, _ = await repository.list_sittings(session, org_id, limit=limit, cursor=None)
    return [_sitting_ref(sitting) for sitting in sittings]


async def supervisor_circuits(
    session: AsyncSession, org_id: uuid.UUID, supervisor_user_id: uuid.UUID
) -> list[SupervisorCircuit]:
    """The circuits this person supervises, with each one's sitting and slot count."""
    pairs = await repository_reads.circuits_for_supervisor(session, org_id, supervisor_user_id)
    counts = await repository_reads.slot_counts_for_circuits(
        session, org_id, [circuit.id for circuit, _ in pairs]
    )
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
        slots=[_slot_ref(slot) for slot in slots],
    )


async def slots_for_trainee(session: AsyncSession, trainee_user_id: uuid.UUID) -> list[TraineeSlot]:
    """Everything this person is rostered onto, in every organisation."""
    slots_with_context = await repository_reads.slots_with_context_for_trainee(session, trainee_user_id)
    return [
        TraineeSlot(slot=_slot_ref(slot), circuit=_circuit_ref(circuit), sitting=_sitting_ref(sitting))
        for slot, circuit, sitting in slots_with_context
    ]


async def sitting_detail(
    session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID
) -> SittingDetail | None:
    """A sitting with every circuit and slot it has, or None if it is not this org's."""
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
                slots=[_slot_ref(slot) for slot in slots],
            )
        )
    return SittingDetail(sitting=_sitting_ref(sitting), circuits=circuits)


async def sitting_ref(session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID) -> SittingRef | None:
    """A sitting as another slice's screen would show it, or None if it is not this org's."""
    sitting = await repository.sitting_by_id(session, org_id, sitting_id)
    return None if sitting is None else _sitting_ref(sitting)


async def slot_and_sitting(
    session: AsyncSession, org_id: uuid.UUID, slot_id: uuid.UUID
) -> tuple[SlotRef, SittingRef] | None:
    """A slot and the sitting it belongs to, or None if the slot is not this org's.

    For the slices whose rule depends on the sitting's mode or its candidate's
    decision: a candidate reading their marks (`attempts`), a review being
    edited after sign-off (`reviews`).
    """
    slot = await repository.slot_by_id(session, org_id, slot_id)
    if slot is None:
        return None
    circuit = await repository.circuit_by_id(session, org_id, slot.circuit_id)
    sitting = None if circuit is None else await repository.sitting_by_id(session, org_id, circuit.sitting_id)
    return None if sitting is None else (_slot_ref(slot), _sitting_ref(sitting))


async def supervisor_for_slot(
    session: AsyncSession, org_id: uuid.UUID, slot_id: uuid.UUID
) -> uuid.UUID | None:
    """Whoever is named to supervise the circuit this slot is being run in.

    Asked by `attempts.service_access`, and the question is
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
    return [_slot_ref(slot) for slot in await repository_reads.slots_for_sitting(session, org_id, sitting_id)]


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
                slots=[_slot_ref(slot) for slot in slots],
            )
        )
    return details


async def run_history(
    session: AsyncSession, org_id: uuid.UUID, *, limit: int, cursor: dict[str, Any] | None
) -> tuple[list[CircuitRun], str | None]:
    """A page of this organisation's finished circuit runs, most recently ended first."""
    runs, next_cursor = await repository_reads.list_run_history(session, org_id, limit=limit, cursor=cursor)
    return [
        CircuitRun(
            id=run.id,
            circuit_id=run.circuit_id,
            circuit_name=run.circuit_name,
            sitting_id=run.sitting_id,
            sitting_name=run.sitting_name,
            mode=run.mode,
            supervisor_user_id=run.supervisor_user_id,
            started_at=run.started_at,
            ended_at=run.ended_at,
            candidate_count=run.candidate_count,
            stations_total=run.stations_total,
            stations_completed=run.stations_completed,
            status=run.status,
        )
        for run in runs
    ], next_cursor


# The clock arithmetic and the alerts, re-exported so `dashboard` can compute
# a board without importing this slice's domain.
alerts_for = domain_alerts.alerts_for
elapsed_seconds = domain_run.elapsed_seconds
remaining_seconds = domain_run.remaining_seconds
FINISHED_SLOT_STATUSES = frozenset(str(status) for status in domain.FINISHED_SLOT_STATUSES)
# A station the candidate actually sat (or is sitting), as opposed to one the circuit moved past.
SAT_SLOT_STATUSES = frozenset({str(domain.SlotStatus.IN_CONSULTATION), str(domain.SlotStatus.COMPLETED)})
