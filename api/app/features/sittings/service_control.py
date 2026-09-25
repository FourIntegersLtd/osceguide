"""Who is driving: the clock, or the person holding the tablet.

`advance_now` is a human saying "this phase is done" without waiting for the
bell. `set_auto_advance` hands the circuit over in one direction or the other
for good — the switch a tutor uses to pause automation and talk between
stations.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ports import RoomAgents
from app.core.settings import Settings
from app.features.sittings import announcements, repository, service_clock, service_run
from app.features.sittings.overrides import (
    ADVANCE,
    AUTO_ADVANCE,
    Actor,
    live_for_update,
    record_change,
    write_intervention,
)
from app.features.sittings.schemas import CircuitRead
from app.features.sittings.service import read_circuit


async def advance_now(
    session: AsyncSession,
    org_id: uuid.UUID,
    circuit_id: uuid.UUID,
    *,
    agents: RoomAgents,
    settings: Settings,
    actor: Actor,
    now: datetime,
) -> CircuitRead:
    """ "This phase is done." Whatever the clock was counting, move on.

    Deliberately not called "end the station": during a break it starts the
    next reading period, and during a reading period it brings the patient in.
    One button that always means the same thing.
    """
    circuit = await live_for_update(session, org_id, circuit_id)
    before = circuit.phase_seq
    await service_run.advance(
        session,
        org_id,
        circuit_id,
        expected_seq=None,
        agents=agents,
        settings=settings,
        now=now,
        by_human=True,
    )
    await write_intervention(
        session,
        org_id,
        circuit,
        action=ADVANCE,
        actor=actor,
        before=before,
        now=now,
        slot_id=circuit.active_slot_id,
    )
    return await read_circuit(session, org_id, circuit_id)


async def set_auto_advance(
    session: AsyncSession,
    org_id: uuid.UUID,
    circuit_id: uuid.UUID,
    *,
    enabled: bool,
    actor: Actor,
    now: datetime,
) -> CircuitRead:
    """Hand the circuit back to a human, or return it to the clock.

    Turning it off does not stop the clock — the countdown a candidate can see
    stays true — it stops the circuit acting on it, so a supervisor decides
    every move. Turning it back on picks up from the deadline already set.
    """
    circuit = await live_for_update(session, org_id, circuit_id)
    before = circuit.phase_seq
    await repository.update_circuit(session, org_id, circuit_id, auto_advance=enabled, phase_seq=before + 1)
    if enabled and circuit.phase_ends_at is not None and circuit.paused_at is None:
        await service_clock.schedule_next(
            session, org_id, circuit_id, seq=before + 1, at=circuit.phase_ends_at
        )
    return await record_change(
        session,
        org_id,
        circuit,
        action=AUTO_ADVANCE,
        actor=actor,
        before=before,
        now=now,
        event=announcements.AUTO_ADVANCE_CHANGED,
    )
