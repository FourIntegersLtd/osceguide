"""Read queries that span a sitting, its circuits and its slots.

Split from `repository.py` by what the queries are for, not by length: these
join across all three tables to answer one screen's question, while the
functions next door load or change a single aggregate. Every org-scoped one
still takes `org_id` first.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.sittings.models import Circuit, CircuitStation, CircuitTrainee, Sitting, Slot


async def count_sittings(session: AsyncSession, org_id: uuid.UUID) -> int:
    stmt = select(func.count()).select_from(Sitting).where(Sitting.org_id == org_id)
    return int((await session.execute(stmt)).scalar_one())


async def circuits_for_supervisor(
    session: AsyncSession, org_id: uuid.UUID, supervisor_user_id: uuid.UUID
) -> list[tuple[Circuit, Sitting]]:
    """The circuits this person is named on, with the sitting each belongs to.

    One query: the supervisor's own screen listed every sitting and then read
    each one to find out which circuits named them.
    """
    stmt = (
        select(Circuit, Sitting)
        .join(Sitting, Sitting.id == Circuit.sitting_id)
        .where(Circuit.org_id == org_id, Circuit.supervisor_user_id == supervisor_user_id)
        .order_by(Circuit.created_at.desc())
    )
    return [(c, s) for c, s in (await session.execute(stmt)).all()]


async def slot_counts_for_circuits(
    session: AsyncSession, org_id: uuid.UUID, circuit_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, int]:
    if not circuit_ids:
        return {}
    stmt = (
        select(Slot.circuit_id, func.count())
        .where(Slot.org_id == org_id, Slot.circuit_id.in_(list(circuit_ids)))
        .group_by(Slot.circuit_id)
    )
    return {circuit_id: int(count) for circuit_id, count in (await session.execute(stmt)).all()}


async def slots_with_context_for_trainee(
    session: AsyncSession, trainee_id: uuid.UUID
) -> list[tuple[Slot, Circuit, Sitting]]:
    """Everything a trainee is rostered onto, across every organisation.

    Not org-scoped, deliberately, and for the same reason `slots_for_trainee`
    is not: a person may be taught by more than one institution, and the portal
    that shows them "what is happening to me" is not inside one of them.
    """
    stmt = (
        select(Slot, Circuit, Sitting)
        .join(Circuit, Circuit.id == Slot.circuit_id)
        .join(Sitting, Sitting.id == Circuit.sitting_id)
        .where(Slot.trainee_id == trainee_id)
        .order_by(Sitting.scheduled_for.desc().nullslast(), Slot.slot_index)
    )
    return [(slot, circuit, sitting) for slot, circuit, sitting in (await session.execute(stmt)).all()]


async def delete_circuit_structure(session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID) -> None:
    """Remove a circuit's slots and its trainee/station lists, before rebuilding.

    The service refuses this unless the circuit is still editable and no slot
    has an attempt, so nothing with a recording behind it is removed here.
    """
    await session.execute(delete(Slot).where(Slot.org_id == org_id, Slot.circuit_id == circuit_id))
    await session.execute(delete(CircuitTrainee).where(CircuitTrainee.circuit_id == circuit_id))
    await session.execute(delete(CircuitStation).where(CircuitStation.circuit_id == circuit_id))
