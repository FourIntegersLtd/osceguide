"""Read queries that span a sitting, its circuits and its slots.

These join across all three tables to answer one screen's question. Every
org-scoped query takes `org_id` first.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import keyset_page
from app.features.sittings.models import (
    Circuit,
    CircuitRunHistory,
    CircuitStation,
    CircuitTrainee,
    Sitting,
    Slot,
)


async def sittings_scheduled_between(
    session: AsyncSession, *, start: datetime, end: datetime, excluding_status: str
) -> list[Sitting]:
    """Every organisation's sittings dated in [start, end) that are not `excluding_status`."""
    stmt = select(Sitting).where(
        Sitting.scheduled_for >= start, Sitting.scheduled_for < end, Sitting.status != excluding_status
    )
    return list((await session.execute(stmt)).scalars())


async def sitting_counts_by_cohort(
    session: AsyncSession, org_id: uuid.UUID, cohort_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """How many sittings are held for each of these cohorts; a cohort with none is absent."""
    if not cohort_ids:
        return {}
    stmt = (
        select(Sitting.cohort_id, func.count())
        .where(Sitting.org_id == org_id, Sitting.cohort_id.in_(list(cohort_ids)))
        .group_by(Sitting.cohort_id)
    )
    return {cohort_id: int(count) for cohort_id, count in (await session.execute(stmt)).all()}


async def count_sittings(session: AsyncSession, org_id: uuid.UUID) -> int:
    """How many sittings this organisation has scheduled."""
    stmt = select(func.count()).select_from(Sitting).where(Sitting.org_id == org_id)
    return int((await session.execute(stmt)).scalar_one())


async def circuits_for_supervisor(
    session: AsyncSession, org_id: uuid.UUID, supervisor_user_id: uuid.UUID
) -> list[tuple[Circuit, Sitting]]:
    """The circuits this person is named on, with the sitting each belongs to."""
    stmt = (
        select(Circuit, Sitting)
        .join(Sitting, Sitting.id == Circuit.sitting_id)
        .where(Circuit.org_id == org_id, Circuit.supervisor_user_id == supervisor_user_id)
        .order_by(Circuit.created_at.desc())
    )
    return [(circuit, sitting) for circuit, sitting in (await session.execute(stmt)).all()]


async def candidate_counts_for_sittings(
    session: AsyncSession, org_id: uuid.UUID, sitting_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """Distinct trainees rostered across each sitting's circuits, keyed by sitting id."""
    if not sitting_ids:
        return {}
    stmt = (
        select(Circuit.sitting_id, func.count(func.distinct(CircuitTrainee.trainee_id)))
        .join(Circuit, Circuit.id == CircuitTrainee.circuit_id)
        .where(Circuit.org_id == org_id, Circuit.sitting_id.in_(list(sitting_ids)))
        .group_by(Circuit.sitting_id)
    )
    return {sitting_id: int(count) for sitting_id, count in (await session.execute(stmt)).all()}


async def totals_for_sittings(
    session: AsyncSession, org_id: uuid.UUID, sitting_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, tuple[int, int]]:
    """(circuits, distinct candidates) per sitting in one aggregate query; a sitting with none is absent."""
    if not sitting_ids:
        return {}
    stmt = (
        select(
            Circuit.sitting_id,
            func.count(func.distinct(Circuit.id)),
            func.count(func.distinct(CircuitTrainee.trainee_id)),
        )
        .outerjoin(CircuitTrainee, Circuit.id == CircuitTrainee.circuit_id)
        .where(Circuit.org_id == org_id, Circuit.sitting_id.in_(list(sitting_ids)))
        .group_by(Circuit.sitting_id)
    )
    return {
        sid: (int(circuits), int(people)) for sid, circuits, people in (await session.execute(stmt)).all()
    }


async def candidate_user_ids_for_sittings(
    session: AsyncSession, org_id: uuid.UUID, sitting_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, set[uuid.UUID]]:
    """The accounts rostered across each sitting's circuits now, keyed by sitting id."""
    if not sitting_ids:
        return {}
    stmt = (
        select(Circuit.sitting_id, CircuitTrainee.trainee_id)
        .join(Circuit, Circuit.id == CircuitTrainee.circuit_id)
        .where(Circuit.org_id == org_id, Circuit.sitting_id.in_(list(sitting_ids)))
    )
    found: dict[uuid.UUID, set[uuid.UUID]] = {}
    for sitting_id, user_id in (await session.execute(stmt)).all():
        found.setdefault(sitting_id, set()).add(user_id)
    return found


async def circuits_led_counts(
    session: AsyncSession, org_id: uuid.UUID, user_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """How many circuits each of these people is named supervisor of, keyed by user id."""
    if not user_ids:
        return {}
    stmt = (
        select(Circuit.supervisor_user_id, func.count())
        .where(Circuit.org_id == org_id, Circuit.supervisor_user_id.in_(list(user_ids)))
        .group_by(Circuit.supervisor_user_id)
    )
    return {user_id: int(count) for user_id, count in (await session.execute(stmt)).all()}


async def trainee_activity(
    session: AsyncSession, org_id: uuid.UUID, user_ids: Sequence[uuid.UUID]
) -> tuple[dict[uuid.UUID, int], dict[uuid.UUID, set[uuid.UUID]]]:
    """Per trainee user: stations sat (completed slots), and the programmes of the
    sittings they are rostered on. Two grouped queries however many trainees."""
    if not user_ids:
        return {}, {}
    ids = list(user_ids)
    sat_stmt = (
        select(Slot.trainee_id, func.count())
        .where(Slot.org_id == org_id, Slot.trainee_id.in_(ids), Slot.status == "completed")
        .group_by(Slot.trainee_id)
    )
    sat = {user_id: int(count) for user_id, count in (await session.execute(sat_stmt)).all()}
    prog_stmt = (
        select(CircuitTrainee.trainee_id, Sitting.programme_id)
        .join(Circuit, Circuit.id == CircuitTrainee.circuit_id)
        .join(Sitting, Sitting.id == Circuit.sitting_id)
        .where(
            Circuit.org_id == org_id,
            CircuitTrainee.trainee_id.in_(ids),
            Sitting.programme_id.is_not(None),
        )
        .distinct()
    )
    programmes: dict[uuid.UUID, set[uuid.UUID]] = {}
    for user_id, programme_id in (await session.execute(prog_stmt)).all():
        programmes.setdefault(user_id, set()).add(programme_id)
    return sat, programmes


async def slot_counts_for_circuits(
    session: AsyncSession, org_id: uuid.UUID, circuit_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """How many slots each of these circuits has, keyed by circuit id."""
    if not circuit_ids:
        return {}
    stmt = (
        select(Slot.circuit_id, func.count())
        .where(Slot.org_id == org_id, Slot.circuit_id.in_(list(circuit_ids)))
        .group_by(Slot.circuit_id)
    )
    return {circuit_id: int(count) for circuit_id, count in (await session.execute(stmt)).all()}


async def slots_with_context_for_trainee(
    session: AsyncSession, trainee_user_id: uuid.UUID
) -> list[tuple[Slot, Circuit, Sitting]]:
    """Everything a trainee is rostered onto, across every organisation.

    Not org-scoped, deliberately: a person may be taught by more than one
    institution, and "what is happening to me" is not inside just one of them.
    """
    stmt = (
        select(Slot, Circuit, Sitting)
        .join(Circuit, Circuit.id == Slot.circuit_id)
        .join(Sitting, Sitting.id == Circuit.sitting_id)
        .where(Slot.trainee_id == trainee_user_id)
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
    """Every slot across every circuit this sitting has, in station order."""
    stmt = (
        select(Slot)
        .join(Circuit, Circuit.id == Slot.circuit_id)
        .where(Slot.org_id == org_id, Circuit.sitting_id == sitting_id)
        .order_by(Slot.slot_index)
    )
    return list((await session.execute(stmt)).scalars())


async def sitting_has_begun(session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID) -> bool:
    """Whether any circuit on this sitting has been started.

    One limited read rather than loading every circuit, since the edit route
    asks this on every write and a sitting can have a dozen circuits.
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

    The edit route asks this for `mode` alone: once anything is composed,
    changing the mode would leave that composition describing something the
    sitting no longer says it is.
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

    Answers nothing on its own: the caller must already hold a role that may
    run a circuit in `org_id`, and being named here is what makes *this*
    attempt readable to them.
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

    What an append may aim at: a latecomer cannot be pointed at a station this
    circuit does not run.
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

    The roster and the slots are separate by design — a trainee is attached to
    a circuit before their first slot exists — so "is this person already
    here" has to ask the roster, not the slots.
    """
    stmt = (
        select(CircuitTrainee.trainee_id)
        .join(Circuit, Circuit.id == CircuitTrainee.circuit_id)
        .where(Circuit.org_id == org_id, CircuitTrainee.circuit_id == circuit_id)
        .order_by(CircuitTrainee.position)
    )
    return list((await session.execute(stmt)).scalars())


async def list_run_history(
    session: AsyncSession, org_id: uuid.UUID, *, limit: int, cursor: dict[str, Any] | None = None
) -> tuple[list[CircuitRunHistory], str | None]:
    """A page of this organisation's finished circuit runs, most recently ended first."""
    stmt = select(CircuitRunHistory).where(CircuitRunHistory.org_id == org_id)
    return await keyset_page(
        session,
        stmt,
        sort_col=CircuitRunHistory.ended_at,
        id_col=CircuitRunHistory.id,
        limit=limit,
        cursor=cursor,
    )


async def programme_activity(
    session: AsyncSession, org_id: uuid.UUID
) -> dict[uuid.UUID, tuple[int, int, list[uuid.UUID]]]:
    """Per programme: sittings held, distinct candidates rostered across them (R-32), and the
    sitting ids, so a per-sitting figure can be rolled up to its programme."""
    stmt = (
        select(
            Sitting.programme_id,
            func.count(func.distinct(Sitting.id)),
            func.count(func.distinct(CircuitTrainee.trainee_id)),
            func.array_agg(func.distinct(Sitting.id)),
        )
        .select_from(Sitting)
        .outerjoin(Circuit, Circuit.sitting_id == Sitting.id)
        .outerjoin(CircuitTrainee, CircuitTrainee.circuit_id == Circuit.id)
        .where(Sitting.org_id == org_id, Sitting.programme_id.is_not(None))
        .group_by(Sitting.programme_id)
    )
    rows = await session.execute(stmt)
    return {programme: (int(held), int(people), list(ids)) for programme, held, people, ids in rows}
