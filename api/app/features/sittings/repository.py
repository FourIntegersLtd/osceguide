"""Storage for sittings, circuits and slots. Org-scoped methods take org_id first."""

from __future__ import annotations

import uuid
from collections.abc import Collection
from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, select, union, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import keyset_page
from app.features.sittings.models import Circuit, CircuitStation, CircuitTrainee, Sitting, Slot


async def count_open_sittings_for_rubric_version(session: AsyncSession, rubric_version_id: uuid.UUID) -> int:
    """Sittings marked against this rubric version that are not cancelled and still have
    a circuit to run, or have none built yet."""
    unfinished = select(Circuit.sitting_id).where(Circuit.ended_at.is_(None))
    any_circuit = select(Circuit.sitting_id)
    stmt = select(func.count(Sitting.id)).where(
        Sitting.rubric_version_id == rubric_version_id,
        Sitting.status != "cancelled",
        Sitting.id.in_(unfinished) | Sitting.id.not_in(any_circuit),
    )
    return int((await session.execute(stmt)).scalar_one())


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
    cohort_id: uuid.UUID | None = None,
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
        cohort_id=cohort_id,
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
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    limit: int,
    cursor: dict[str, Any] | None = None,
    status: str | None = None,
    programme_id: uuid.UUID | None = None,
    scheduled_from: datetime | None = None,
    scheduled_to: datetime | None = None,
) -> tuple[list[Sitting], str | None]:
    """A page of this organisation's sittings, newest first, narrowed by the filters given (R-31)."""
    stmt = select(Sitting).where(Sitting.org_id == org_id)
    if status is not None:
        stmt = stmt.where(Sitting.status == status)
    if programme_id is not None:
        stmt = stmt.where(Sitting.programme_id == programme_id)
    if scheduled_from is not None:
        stmt = stmt.where(Sitting.scheduled_for >= scheduled_from)
    if scheduled_to is not None:
        stmt = stmt.where(Sitting.scheduled_for < scheduled_to)
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


async def delete_circuit(session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID) -> None:
    """Remove the circuit row; the service has already cleared its structure."""
    await session.execute(delete(Circuit).where(Circuit.org_id == org_id, Circuit.id == circuit_id))


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


async def slot_by_id_for_user(session: AsyncSession, slot_id: uuid.UUID, user_id: uuid.UUID) -> Slot | None:
    """The slot with this id, if it is this signed-in person's own.

    For a `/me` route, which has no `org_slug` to scope by first — `trainee_id`
    on a slot is `users.id` (unlike a result decision's `trainee_id`), so this
    checks ownership directly rather than requiring the org lookup `slot_by_id`
    does first.
    """
    stmt = select(Slot).where(Slot.id == slot_id, Slot.trainee_id == user_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def update_slots_for_circuit(
    session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID, **values: Any
) -> None:
    """Write the given fields onto every slot of this circuit at once."""
    await session.execute(
        update(Slot).where(Slot.org_id == org_id, Slot.circuit_id == circuit_id).values(**values)
    )


async def update_slot(
    session: AsyncSession,
    org_id: uuid.UUID,
    slot_id: uuid.UUID,
    *,
    only_if_status: str | None = None,
    **values: Any,
) -> None:
    """Write the given fields onto one slot; with `only_if_status`, only while it has that status."""
    stmt = update(Slot).where(Slot.org_id == org_id, Slot.id == slot_id)
    if only_if_status is not None:
        stmt = stmt.where(Slot.status == only_if_status)
    await session.execute(stmt.values(**values))


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


async def rubric_versions_for_slots(
    session: AsyncSession, org_id: uuid.UUID, slot_ids: Collection[uuid.UUID]
) -> dict[uuid.UUID, uuid.UUID]:
    """The rubric version each slot is marked against, in one query (see `rubric_version_for_slot`)."""
    if not slot_ids:
        return {}
    stmt = (
        select(Slot.id, Sitting.rubric_version_id)
        .join(Circuit, Circuit.id == Slot.circuit_id)
        .join(Sitting, Sitting.id == Circuit.sitting_id)
        .where(Slot.org_id == org_id, Slot.id.in_(list(slot_ids)))
    )
    return {slot_id: version_id for slot_id, version_id in (await session.execute(stmt)).all()}


async def circuit_counts_by_station_version(
    session: AsyncSession, station_version_ids: Collection[uuid.UUID], *, open_only: bool = False
) -> dict[uuid.UUID, int]:
    """How many circuits, in any organisation, name each station version.

    `open_only` leaves out circuits that have ended: their history still reads the version, and
    only a circuit yet to run (or running) is broken by its being withdrawn.

    A circuit names a version through its station list and through each slot,
    so both are read and a circuit is counted once.
    """
    if not station_version_ids:
        return {}
    ids = list(station_version_ids)
    uses = union(
        select(CircuitStation.station_version_id, CircuitStation.circuit_id).where(
            CircuitStation.station_version_id.in_(ids)
        ),
        select(Slot.station_version_id, Slot.circuit_id).where(Slot.station_version_id.in_(ids)),
    ).subquery()
    stmt = select(uses.c.station_version_id, func.count(uses.c.circuit_id.distinct())).group_by(
        uses.c.station_version_id
    )
    if open_only:
        stmt = stmt.join(Circuit, Circuit.id == uses.c.circuit_id).where(Circuit.ended_at.is_(None))
    return {version_id: int(count) for version_id, count in (await session.execute(stmt)).all()}
