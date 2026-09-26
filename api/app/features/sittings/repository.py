"""Storage for sittings, circuits and slots. Org-scoped methods take org_id first."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import keyset_page
from app.features.sittings.models import Circuit, CircuitStation, CircuitTrainee, Sitting, Slot


async def create_sitting(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    name: str,
    rubric_version_id: uuid.UUID,
    mode: str,
    sitting_type: str,
    scheduled_for: datetime | None,
    programme_id: uuid.UUID | None,
) -> Sitting:
    """Write a new sitting row and return it, refreshed with its defaults."""
    sitting = Sitting(
        org_id=org_id,
        name=name,
        rubric_version_id=rubric_version_id,
        mode=mode,
        sitting_type=sitting_type,
        scheduled_for=scheduled_for,
        programme_id=programme_id,
    )
    session.add(sitting)
    await session.flush()
    await session.refresh(sitting)
    return sitting


async def sitting_by_id(session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID) -> Sitting | None:
    """The sitting with this id, or None if it does not belong to this organisation."""
    stmt = select(Sitting).where(Sitting.org_id == org_id, Sitting.id == sitting_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_sittings(
    session: AsyncSession, org_id: uuid.UUID, *, limit: int, cursor: dict[str, Any] | None = None
) -> tuple[list[Sitting], str | None]:
    """A page of this organisation's sittings, newest first."""
    stmt = select(Sitting).where(Sitting.org_id == org_id)
    return await keyset_page(
        session, stmt, sort_col=Sitting.created_at, id_col=Sitting.id, limit=limit, cursor=cursor
    )


async def set_sitting_status(
    session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID, *, status: str
) -> None:
    """Write the sitting's status directly, without touching anything else."""
    await session.execute(
        update(Sitting).where(Sitting.org_id == org_id, Sitting.id == sitting_id).values(status=status)
    )


async def update_sitting(
    session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID, **values: Any
) -> None:
    """Write the fields an edit screen may change; which ones is the service's rule.

    The two questions the edit asks first — has this sitting begun, how many
    circuits it has — span the circuit table and live in `repository_reads.py`
    instead.
    """
    await session.execute(
        update(Sitting).where(Sitting.org_id == org_id, Sitting.id == sitting_id).values(**values)
    )


# --- circuits --------------------------------------------------------------


async def create_circuit(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    sitting_id: uuid.UUID,
    name: str,
    supervisor_user_id: uuid.UUID | None,
    timing: dict[str, Any],
) -> Circuit:
    """Write a new circuit row and return it, refreshed with its defaults."""
    circuit = Circuit(
        org_id=org_id,
        sitting_id=sitting_id,
        name=name,
        supervisor_user_id=supervisor_user_id,
        timing=timing,
    )
    session.add(circuit)
    await session.flush()
    await session.refresh(circuit)
    return circuit


async def circuit_by_id(session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID) -> Circuit | None:
    """The circuit with this id, or None if it does not belong to this organisation."""
    stmt = select(Circuit).where(Circuit.org_id == org_id, Circuit.id == circuit_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def circuit_for_update(
    session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID
) -> Circuit | None:
    """The circuit row, locked until the transaction ends (C4).

    Every operation that reads the circuit's state and then writes it takes
    this. Without it two supervisors on a live exam interleave: the damage is
    not two active slots, it is `end_circuit` clearing the active slot while
    `switch_turn` sets one, leaving a circuit that is over and still showing
    somebody consulting in a room that has been torn down.
    """
    stmt = select(Circuit).where(Circuit.org_id == org_id, Circuit.id == circuit_id).with_for_update()
    return (await session.execute(stmt)).scalar_one_or_none()


async def circuits_for_sitting(
    session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID
) -> list[Circuit]:
    """Every circuit this sitting has, oldest first."""
    stmt = (
        select(Circuit)
        .where(Circuit.org_id == org_id, Circuit.sitting_id == sitting_id)
        .order_by(Circuit.created_at)
    )
    return list((await session.execute(stmt)).scalars())


async def update_circuit(
    session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID, **values: Any
) -> None:
    """Write the given fields onto the circuit row; which ones is the caller's rule."""
    await session.execute(
        update(Circuit).where(Circuit.org_id == org_id, Circuit.id == circuit_id).values(**values)
    )


async def add_circuit_members(
    session: AsyncSession,
    circuit_id: uuid.UUID,
    *,
    trainee_ids: list[uuid.UUID],
    station_version_ids: list[uuid.UUID],
) -> None:
    """Record who is rostered on this circuit and which stations it runs, in order."""
    for position, trainee_id in enumerate(trainee_ids):
        session.add(CircuitTrainee(circuit_id=circuit_id, trainee_id=trainee_id, position=position))
    for position, station_version_id in enumerate(station_version_ids):
        session.add(
            CircuitStation(circuit_id=circuit_id, position=position, station_version_id=station_version_id)
        )
    await session.flush()


async def create_slots(
    session: AsyncSession,
    org_id: uuid.UUID,
    circuit_id: uuid.UUID,
    *,
    planned: list[tuple[int, uuid.UUID, uuid.UUID]],
    room_name: str | None = None,
) -> list[Slot]:
    """Build slots, optionally already in a room.

    `room_name` is for appending to a circuit that is already running (C8): a
    slot with no room is one the trainee portal cannot offer, so a latecomer
    would sit outside a session in progress.
    """
    slots = [
        Slot(
            org_id=org_id,
            circuit_id=circuit_id,
            slot_index=index,
            trainee_id=trainee_id,
            station_version_id=station_version_id,
            room_name=room_name,
        )
        for index, trainee_id, station_version_id in planned
    ]
    session.add_all(slots)
    await session.flush()
    for slot in slots:
        await session.refresh(slot)
    return slots


async def slots_for_circuit(session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID) -> list[Slot]:
    """Every slot on this circuit, in station order."""
    stmt = select(Slot).where(Slot.org_id == org_id, Slot.circuit_id == circuit_id).order_by(Slot.slot_index)
    return list((await session.execute(stmt)).scalars())


async def slot_by_id(session: AsyncSession, org_id: uuid.UUID, slot_id: uuid.UUID) -> Slot | None:
    """The slot with this id, or None if it does not belong to this organisation."""
    stmt = select(Slot).where(Slot.org_id == org_id, Slot.id == slot_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def update_slots_for_circuit(
    session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID, **values: Any
) -> None:
    """Write the given fields onto every slot of this circuit at once."""
    await session.execute(
        update(Slot).where(Slot.org_id == org_id, Slot.circuit_id == circuit_id).values(**values)
    )


async def update_slot(session: AsyncSession, org_id: uuid.UUID, slot_id: uuid.UUID, **values: Any) -> None:
    """Write the given fields onto one slot."""
    await session.execute(update(Slot).where(Slot.org_id == org_id, Slot.id == slot_id).values(**values))


async def rubric_version_for_slot(
    session: AsyncSession, org_id: uuid.UUID, slot_id: uuid.UUID
) -> uuid.UUID | None:
    """The rubric version a slot is marked against: its sitting's bound rubric."""
    stmt = (
        select(Sitting.rubric_version_id)
        .join(Circuit, Circuit.sitting_id == Sitting.id)
        .join(Slot, Slot.circuit_id == Circuit.id)
        .where(Slot.org_id == org_id, Slot.id == slot_id)
    )
    return (await session.execute(stmt)).scalar_one_or_none()
