"""Taking hold of the clock on a circuit that is running itself.

Every one of these exists because something goes wrong on exam day: the fire
alarm goes, a candidate's microphone dies, a station has to be given back.
Automation without them would be worse than the manual runner it replaces — a
circuit nobody could rescue.

Three things are true of all of them.

**They bump `phase_seq`**, so the transition already scheduled for the old
deadline arrives holding a number that no longer matches and does nothing. That
is how a human beats the clock.

**They reschedule**, so the circuit keeps running itself afterwards. An
override that left it stopped would be a trap.

**They are recorded.** When a candidate says their station went wrong, the
question is what was done to it and by whom.

Rescuing one station — the patient, the recording, the order — is
`service_rescue.py`.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import raise_mapped
from app.features.sittings import (
    announcements,
    domain_run,
    errors,
    repository,
    service_steps,
)
from app.features.sittings.overrides import (
    EXTEND_CLOCK,
    PAUSE,
    RESET_CLOCK,
    RESUME,
    current_step,
    live_for_update,
    record_change,
)
from app.features.sittings.overrides import (
    Actor as Actor,
)
from app.features.sittings.overrides import (
    list_interventions as list_interventions,
)
from app.features.sittings.reads import timing_domain
from app.features.sittings.schemas import CircuitRead
from app.features.sittings.service import _REFUSALS


async def pause(
    session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID, *, actor: Actor, now: datetime
) -> CircuitRead:
    """Stop the clock. Nothing advances until it is resumed.

    The scheduled transition is not cancelled — it cannot be — but it will find
    a sequence that has moved and do nothing, and a paused circuit refuses to
    advance anyway. Two guards for one failure, because the failure is a
    candidate's consultation ending during a fire alarm.
    """
    circuit = await live_for_update(session, org_id, circuit_id)
    try:
        domain_run.ensure_not_paused(circuit.paused_at)
    except domain_run.CircuitPaused as exc:
        raise_mapped(exc, _REFUSALS)

    before = circuit.phase_seq
    await repository.update_circuit(session, org_id, circuit_id, paused_at=now, phase_seq=before + 1)
    return await record_change(
        session,
        org_id,
        circuit,
        action=PAUSE,
        actor=actor,
        before=before,
        now=now,
        event=announcements.PAUSED,
    )


async def resume(
    session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID, *, actor: Actor, now: datetime
) -> CircuitRead:
    """Start the clock again, with the deadline pushed out by the pause.

    Exactly by the pause: a stoppage must not cost a candidate their
    consultation, and must not hand them extra time either.
    """
    circuit = await live_for_update(session, org_id, circuit_id)
    try:
        domain_run.ensure_paused(circuit.paused_at)
    except domain_run.CircuitNotPaused as exc:
        raise_mapped(exc, _REFUSALS)

    before = circuit.phase_seq
    paused_at = circuit.paused_at
    assert paused_at is not None  # ensure_paused
    spent = int((now - paused_at).total_seconds())
    ends = (
        domain_run.resumed_deadline(circuit.phase_ends_at, paused_at=paused_at, now=now)
        if circuit.phase_ends_at
        else None
    )
    await repository.update_circuit(
        session,
        org_id,
        circuit_id,
        paused_at=None,
        paused_seconds=circuit.paused_seconds + spent,
        phase_ends_at=ends,
        phase_seq=before + 1,
    )
    if ends is not None:
        await service_steps.schedule_next(session, org_id, circuit_id, seq=before + 1, at=ends)
    return await record_change(
        session,
        org_id,
        circuit,
        action=RESUME,
        actor=actor,
        before=before,
        now=now,
        event=announcements.RESUMED,
    )


async def extend_clock(
    session: AsyncSession,
    org_id: uuid.UUID,
    circuit_id: uuid.UUID,
    *,
    seconds: int,
    actor: Actor,
    now: datetime,
) -> CircuitRead:
    """Give this phase more time, without restarting it.

    Works while paused too: an extension decided during a stoppage should not
    have to wait for the resume to be applied.
    """
    circuit = await live_for_update(session, org_id, circuit_id)
    if circuit.phase_ends_at is None:
        raise errors.CircuitNotLive()

    before = circuit.phase_seq
    ends = circuit.phase_ends_at + timedelta(seconds=seconds)
    await repository.update_circuit(session, org_id, circuit_id, phase_ends_at=ends, phase_seq=before + 1)
    if circuit.paused_at is None:
        await service_steps.schedule_next(session, org_id, circuit_id, seq=before + 1, at=ends)
    return await record_change(
        session,
        org_id,
        circuit,
        action=EXTEND_CLOCK,
        actor=actor,
        before=before,
        now=now,
        event=announcements.CLOCK_CHANGED,
    )


async def reset_clock(
    session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID, *, actor: Actor, now: datetime
) -> CircuitRead:
    """Run this phase again from the top, for its full length.

    For the case where the phase was lost rather than shortened: a candidate
    who could not hear the patient for the first four minutes needs the ten
    back, not six.
    """
    circuit = await live_for_update(session, org_id, circuit_id)
    if circuit.phase is None:
        raise errors.CircuitNotLive()

    before = circuit.phase_seq
    step = current_step(circuit)
    started, ends = domain_run.step_window(step, timing=timing_domain(circuit.timing), now=now)
    await repository.update_circuit(
        session,
        org_id,
        circuit_id,
        phase_started_at=started,
        phase_ends_at=ends,
        phase_seq=before + 1,
        paused_at=None,
        paused_seconds=0,
    )
    await service_steps.schedule_next(session, org_id, circuit_id, seq=before + 1, at=ends)
    return await record_change(
        session,
        org_id,
        circuit,
        action=RESET_CLOCK,
        actor=actor,
        before=before,
        now=now,
        event=announcements.CLOCK_CHANGED,
    )
