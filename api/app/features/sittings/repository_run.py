"""Storage for a circuit while it is running, and for what was done to it.

Serves the orchestrator and the exam-day board — "which circuits are overdue
a transition", "which have been live all night". Two queries are deliberately
not org-scoped, and say so.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.sittings.models import (
    Circuit,
    CircuitIntervention,
    CircuitRunHistory,
    CircuitTrainee,
    Sitting,
    Slot,
)


@dataclass(frozen=True)
class DueCircuit:
    """A circuit the sweeper should look at, and the sequence it was at when asked."""

    org_id: uuid.UUID
    circuit_id: uuid.UUID
    phase_seq: int


def _live() -> Any:
    return and_(Circuit.started_at.is_not(None), Circuit.ended_at.is_(None))


async def live_circuits_for_org(session: AsyncSession, org_id: uuid.UUID) -> list[tuple[Circuit, Sitting]]:
    """Every circuit this organisation currently has running, with its sitting.

    The exam-day board's one query. A partial index covers exactly this
    predicate, because a live circuit is a vanishing fraction of the table and
    the board asks every time anything changes.
    """
    stmt = (
        select(Circuit, Sitting)
        .join(Sitting, Sitting.id == Circuit.sitting_id)
        .where(Circuit.org_id == org_id, _live())
        .order_by(Sitting.scheduled_for.desc().nullslast(), Circuit.created_at)
    )
    return [(circuit, sitting) for circuit, sitting in (await session.execute(stmt)).all()]


async def sitting_mode_for_circuit(session: AsyncSession, circuit_id: uuid.UUID) -> str | None:
    """The mode (`training`/`exam`) of the sitting a circuit belongs to.

    One column, not the row, because the only caller (the observer grant)
    needs a single fact to decide a publish permission — see `service_join`.
    `None` if the circuit does not exist, which the caller treats as the
    safer default (no publish).
    """
    stmt = (
        select(Sitting.mode).join(Circuit, Circuit.sitting_id == Sitting.id).where(Circuit.id == circuit_id)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def overdue_circuits(session: AsyncSession, *, now: datetime, grace_seconds: int) -> list[DueCircuit]:
    """Live circuits whose phase ended and which nothing has moved on.

    Not org-scoped: the sweeper is a background job with no tenant, and
    scoping it per organisation would mean enumerating organisations to find
    the ones with an examination running.

    The grace is what keeps this from racing the scheduled transition that is
    about to do the same work: a job due at the deadline gets its moment first,
    and only silence past the grace brings the sweeper in.
    """
    cutoff = now - timedelta(seconds=grace_seconds)
    stmt = select(Circuit.org_id, Circuit.id, Circuit.phase_seq).where(
        _live(),
        Circuit.paused_at.is_(None),
        Circuit.auto_advance.is_(True),
        Circuit.phase_ends_at.is_not(None),
        Circuit.phase_ends_at < cutoff,
    )
    return [
        DueCircuit(org_id=org_id, circuit_id=circuit_id, phase_seq=seq)
        for org_id, circuit_id, seq in (await session.execute(stmt)).all()
    ]


async def stale_circuits(session: AsyncSession, *, started_before: datetime) -> list[DueCircuit]:
    """Circuits left running long after anybody went home.

    Without this, a morning nobody closed keeps a room open and a candidate's
    portal offering a join button forever.
    """
    stmt = select(Circuit.org_id, Circuit.id, Circuit.phase_seq).where(
        _live(), Circuit.started_at < started_before
    )
    return [
        DueCircuit(org_id=org_id, circuit_id=circuit_id, phase_seq=seq)
        for org_id, circuit_id, seq in (await session.execute(stmt)).all()
    ]


async def circuit_for_rostered_trainee(
    session: AsyncSession, circuit_id: uuid.UUID, trainee_user_id: uuid.UUID
) -> Circuit | None:
    """The circuit, if this person is actually on it.

    Not org-scoped, for the same reason the trainee portal is not: a candidate
    is not inside an organisation's URL space, and asking them to supply a slug
    to join their own examination would be asking them to prove something the
    roster already knows.
    """
    stmt = (
        select(Circuit)
        .join(Slot, Slot.circuit_id == Circuit.id)
        .where(Circuit.id == circuit_id, Slot.trainee_id == trainee_user_id)
        .limit(1)
    )
    found = (await session.execute(stmt)).scalar_one_or_none()
    if found is not None:
        return found
    # A training circuit's latecomer is a member before they have a slot.
    stmt = (
        select(Circuit)
        .join(CircuitTrainee, CircuitTrainee.circuit_id == Circuit.id)
        .where(Circuit.id == circuit_id, CircuitTrainee.trainee_id == trainee_user_id)
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def mark_slots_skipped(
    session: AsyncSession,
    org_id: uuid.UUID,
    circuit_id: uuid.UUID,
    *,
    before_index: int,
    statuses: Sequence[str],
) -> None:
    """Close off stations the circuit has moved past without sitting.

    `statuses` is the set still considered open, passed in rather than spelled
    here: which statuses mean "not yet sat" is the domain's rule, and a second
    copy in SQL is one that will not be updated when the first changes.
    """
    await session.execute(
        update(Slot)
        .where(
            Slot.org_id == org_id,
            Slot.circuit_id == circuit_id,
            Slot.slot_index < before_index,
            Slot.status.in_(list(statuses)),
        )
        .values(status="skipped")
    )


async def record_intervention(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    circuit_id: uuid.UUID,
    slot_id: uuid.UUID | None,
    actor_user_id: uuid.UUID | None,
    action: str,
    reason: str | None,
    phase_seq_before: int,
    phase_seq_after: int,
    at: datetime,
) -> CircuitIntervention:
    """Write one intervention row and return it, refreshed with its defaults."""
    intervention = CircuitIntervention(
        org_id=org_id,
        circuit_id=circuit_id,
        slot_id=slot_id,
        actor_user_id=actor_user_id,
        action=action,
        reason=reason,
        phase_seq_before=phase_seq_before,
        phase_seq_after=phase_seq_after,
        at=at,
    )
    session.add(intervention)
    await session.flush()
    await session.refresh(intervention)
    return intervention


async def interventions_for_circuit(
    session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID
) -> list[CircuitIntervention]:
    """Everything recorded against this circuit, newest first."""
    stmt = (
        select(CircuitIntervention)
        .where(CircuitIntervention.org_id == org_id, CircuitIntervention.circuit_id == circuit_id)
        .order_by(CircuitIntervention.at.desc())
    )
    return list((await session.execute(stmt)).scalars())


async def record_run_history(session: AsyncSession, org_id: uuid.UUID, **values: Any) -> None:
    """Write one finished run of a circuit. Never updated afterwards."""
    session.add(CircuitRunHistory(org_id=org_id, **values))
    await session.flush()
