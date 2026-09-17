"""What another slice may ask about sittings in bulk.

The projections themselves live in `dashboard`; this is the part of them that
only this slice can answer, returned as plain dataclasses. A read model that
reached into `sittings`' tables for a supervisor's circuits would become a
second owner of them, and the tenant scoping would have two homes.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.sittings import repository, repository_reads
from app.features.sittings.models import Circuit, Sitting, Slot
from app.features.sittings.reads import timing_read
from app.features.sittings.schemas import TimingRead


@dataclass(frozen=True)
class SittingRef:
    """A sitting as a line on somebody else's screen."""

    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    mode: str
    sitting_type: str
    status: str
    scheduled_for: datetime | None
    feedback_template_version_id: uuid.UUID


@dataclass(frozen=True)
class CircuitRef:
    id: uuid.UUID
    sitting_id: uuid.UUID
    name: str
    supervisor_user_id: uuid.UUID | None
    # Already resolved to the defaults a circuit runs with, so a caller does
    # not re-implement the clamping this slice owns.
    timing: TimingRead
    active_slot_id: uuid.UUID | None
    room_name: str | None
    agent_dispatched_at: datetime | None
    started_at: datetime | None
    ended_at: datetime | None


@dataclass(frozen=True)
class SlotRef:
    id: uuid.UUID
    circuit_id: uuid.UUID
    slot_index: int
    trainee_id: uuid.UUID
    station_version_id: uuid.UUID
    status: str
    room_name: str | None
    started_at: datetime | None
    ended_at: datetime | None
    exam_completed_at: datetime | None


@dataclass(frozen=True)
class SupervisorCircuit:
    """One row of "circuits assigned to me"."""

    circuit: CircuitRef
    sitting: SittingRef
    slot_count: int


@dataclass(frozen=True)
class CircuitDetail:
    """Everything one console screen needs from this slice."""

    circuit: CircuitRef
    sitting: SittingRef
    slots: list[SlotRef] = field(default_factory=list)


@dataclass(frozen=True)
class TraineeSlot:
    """A slot a trainee is rostered onto, with the sitting it belongs to."""

    slot: SlotRef
    circuit: CircuitRef
    sitting: SittingRef


def _sitting_ref(row: Sitting) -> SittingRef:
    return SittingRef(
        id=row.id,
        org_id=row.org_id,
        name=row.name,
        mode=row.mode,
        sitting_type=row.sitting_type,
        status=row.status,
        scheduled_for=row.scheduled_for,
        feedback_template_version_id=row.feedback_template_version_id,
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
