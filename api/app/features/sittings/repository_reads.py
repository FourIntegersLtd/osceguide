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


async def slots_for_sitting(session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID) -> list[Slot]:
    stmt = (
        select(Slot)
        .join(Circuit, Circuit.id == Slot.circuit_id)
        .where(Slot.org_id == org_id, Circuit.sitting_id == sitting_id)
        .order_by(Slot.slot_index)
    )
    return list((await session.execute(stmt)).scalars())


async def sitting_has_begun(session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID) -> bool:
    """Whether any circuit on this sitting has been started.

    One limited read rather than a load of the circuits: the edit route asks it
    to decide what it may write, and a sitting with twelve circuits is exactly
    the case where asking is expensive.
    """
    stmt = (
        select(Circuit.id)
        .where(
            Circuit.org_id == org_id,
            Circuit.sitting_id == sitting_id,
            Circuit.started_at.is_not(None),
        )
        .limit(1)
    )
    return (await session.execute(stmt)).first() is not None


async def count_sitting_circuits(session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID) -> int:
    """How many circuits this sitting is composed of.

    The edit route asks it about `mode` alone: the mode is what a circuit is
    composed *from*, so once there is anything composed, changing it would leave
    the composition describing something the sitting no longer says it is.
    """
    stmt = (
        select(func.count())
        .select_from(Circuit)
        .where(Circuit.org_id == org_id, Circuit.sitting_id == sitting_id)
    )
    return int((await session.execute(stmt)).scalar_one())


async def circuit_supervisor_for_slot(
    session: AsyncSession, org_id: uuid.UUID, slot_id: uuid.UUID
) -> uuid.UUID | None:
    """The user named as supervisor of the circuit a slot belongs to.

    Asked by `attempts`, which sits below this slice and cannot read the tables
    itself — it reaches this through the seam in `composition.py`. It answers
    nothing on its own: a caller must already hold a role that may run a circuit
    in `org_id`, and being named here is what makes *this* attempt readable.
    """
    stmt = (
        select(Circuit.supervisor_user_id)
        .join(Slot, Slot.circuit_id == Circuit.id)
        .where(Slot.org_id == org_id, Slot.id == slot_id)
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def circuit_station_ids(
    session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID
) -> list[uuid.UUID]:
    """The stations this circuit runs, in position order.

    What an append is allowed to aim at: b2b's dialog could name any station in
    the organisation, and this one is the circuit's own list, so a latecomer
    cannot be pointed at a station nobody here is sitting.
    """
    stmt = (
        select(CircuitStation.station_version_id)
        .join(Circuit, Circuit.id == CircuitStation.circuit_id)
        .where(Circuit.org_id == org_id, CircuitStation.circuit_id == circuit_id)
        .order_by(CircuitStation.position)
    )
    return list((await session.execute(stmt)).scalars())


async def circuit_trainee_ids(
    session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID
) -> list[uuid.UUID]:
    """Everyone already on this circuit, whether or not they have a slot yet.

    The roster list and the slots are two rows apiece by design — a trainee is
    attached to a circuit before the circuit is started and their first slot
    exists — so "is this person already here" has to ask the roster list, which
    is what b2b's duplicate refusal asked.
    """
    stmt = (
        select(CircuitTrainee.trainee_id)
        .join(Circuit, Circuit.id == CircuitTrainee.circuit_id)
        .where(Circuit.org_id == org_id, CircuitTrainee.circuit_id == circuit_id)
        .order_by(CircuitTrainee.position)
    )
    return list((await session.execute(stmt)).scalars())
