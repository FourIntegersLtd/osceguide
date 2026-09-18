"""Writing the examination clock, and owing the transition that ends it.

The two always happen together, which is the point of them being one module:
a phase written without its transition is a circuit that stops, and a
transition scheduled without the phase it belongs to is one that fires against
a state nobody put it in. They are written in the same transaction, so either
both land or neither does (ADR 0006).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jobs import defer_in_transaction
from app.features.sittings import domain_run, repository
from app.features.sittings.models import Circuit
from app.features.sittings.reads import timing_domain

ADVANCE_QUEUE = "circuits"
ADVANCE_TASK = "advance_circuit"


async def set_phase(
    session: AsyncSession,
    org_id: uuid.UUID,
    circuit: Circuit,
    step: domain_run.Step,
    *,
    seq: int,
    now: datetime,
    active_slot_id: uuid.UUID | None,
    agent_dispatched_at: datetime | None = None,
) -> None:
    """Write the clock, and owe the transition that ends it."""
    started, ends = domain_run.step_window(step, timing=timing_domain(circuit.timing), now=now)
    phase = domain_run.phase_of(step)
    await repository.update_circuit(
        session,
        org_id,
        circuit.id,
        phase=str(phase) if phase else None,
        phase_started_at=started,
        phase_ends_at=ends,
        phase_seq=seq,
        paused_at=None,
        paused_seconds=0,
        active_slot_id=active_slot_id,
        agent_dispatched_at=agent_dispatched_at,
    )
    # The caller reads this row again to announce and to schedule, so the
    # in-memory copy has to agree with what was just written.
    circuit.phase = str(phase) if phase else None
    circuit.phase_started_at = started
    circuit.phase_ends_at = ends
    circuit.phase_seq = seq
    circuit.paused_at = None
    circuit.paused_seconds = 0
    circuit.active_slot_id = active_slot_id
    await schedule_next(session, org_id, circuit.id, seq=seq, at=ends)


async def schedule_next(
    session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID, *, seq: int, at: datetime
) -> None:
    """Owe a transition at the moment this phase ends.

    Written in the caller's transaction, so a phase that rolls back takes its
    transition with it. `lock` serialises one circuit's transitions against each
    other; `queueing_lock` is unique per sequence, so the same phase cannot be
    scheduled twice.
    """
    await defer_in_transaction(
        session,
        queue=ADVANCE_QUEUE,
        task=ADVANCE_TASK,
        args={"org_id": str(org_id), "circuit_id": str(circuit_id), "expected_seq": seq},
        lock=f"circuit:{circuit_id}",
        queueing_lock=f"advance:{circuit_id}:{seq}",
        scheduled_at=at,
    )
