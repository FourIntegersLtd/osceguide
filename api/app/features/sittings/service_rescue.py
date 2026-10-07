"""Rescuing a station that has gone wrong.

The patient did not arrive, the recording is unusable, the wrong station is
showing. Each leaves the circuit running afterwards — an override that
stopped it would be a trap.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import raise_mapped
from app.core.ports import RoomAgents
from app.core.settings import Settings
from app.features.attempts import service as attempts_service
from app.features.sittings import (
    announcements,
    domain,
    domain_run,
    errors,
    repository,
    repository_run,
    service_steps,
)
from app.features.sittings.overrides import (
    JUMP_TO,
    REDO_STATION,
    RESEND_PATIENT,
    Actor,
    live_for_update,
    write_intervention,
)
from app.features.sittings.schemas import CircuitRead, DispatchResult
from app.features.sittings.service import _REFUSALS, read_circuit


async def resend_patient(
    session: AsyncSession,
    org_id: uuid.UUID,
    circuit_id: uuid.UUID,
    *,
    agents: RoomAgents,
    settings: Settings,
    actor: Actor,
    now: datetime,
) -> DispatchResult:
    """Put a fresh patient into the room, for the station already running.

    The clock is deliberately untouched: the candidate has been in the room the
    whole time and the station is still the one they are sitting. The previous
    attempt is failed rather than overwritten, so the silence is kept as
    evidence beside the retry.
    """
    circuit = await live_for_update(session, org_id, circuit_id)
    if circuit.phase != domain_run.RunPhase.SIMULATION or circuit.active_slot_id is None:
        raise errors.NoActiveStation()

    slot = await repository.slot_by_id(session, org_id, circuit.active_slot_id)
    if slot is None:
        raise errors.SlotNotFound()

    attempt_id, agent_name, removed = await service_steps.dispatch_patient(
        session, org_id, circuit, slot, agents=agents, settings=settings, now=now
    )
    before = circuit.phase_seq
    await repository.update_circuit(
        session, org_id, circuit_id, agent_dispatched_at=now, phase_seq=before + 1
    )
    # The deadline has not moved, so the transition already queued is still the
    # right one — but its sequence has, so it is scheduled again under the new.
    if circuit.phase_ends_at is not None and circuit.paused_at is None:
        await service_steps.schedule_next(
            session, org_id, circuit_id, seq=before + 1, at=circuit.phase_ends_at
        )
    await write_intervention(
        session,
        org_id,
        circuit,
        action=RESEND_PATIENT,
        actor=actor,
        before=before,
        now=now,
        slot_id=slot.id,
    )
    await announcements.circuit_changed(session, org_id, circuit_id, name=announcements.PATIENT_RESENT)
    return DispatchResult(
        room_name=circuit.room_name or "",
        slot_id=slot.id,
        attempt_id=attempt_id,
        agent_name=agent_name,
        stale_agents_removed=removed,
    )


async def redo_station(
    session: AsyncSession,
    org_id: uuid.UUID,
    circuit_id: uuid.UUID,
    *,
    slot_id: uuid.UUID,
    agents: RoomAgents,
    settings: Settings,
    actor: Actor,
    now: datetime,
) -> CircuitRead:
    """Start a station again from its reading period.

    Distinct from resending the patient: that keeps the consultation running,
    this gives the station back. The live recording is failed with `redo`, so
    what happened the first time is still there to look at.
    """
    circuit = await live_for_update(session, org_id, circuit_id)
    slot = await repository.slot_by_id(session, org_id, slot_id)
    if slot is None or slot.circuit_id != circuit_id:
        raise errors.SlotNotFound()

    before = circuit.phase_seq
    # The redone station's recording first, so it is filed as a redo rather than an interruption.
    await attempts_service.fail_live_for_slot(session, slot_id=slot_id, now=now, reason="redo")
    await service_steps.clear_patient(session, org_id, circuit, agents=agents, now=now, station_sat=False)
    await repository.update_slot(
        session,
        org_id,
        slot_id,
        status=domain.SlotStatus.SCHEDULED,
        ended_at=None,
        exam_completed_at=None,
    )
    slots = await repository.slots_for_circuit(session, org_id, circuit_id)
    await service_steps.apply_step(
        session,
        org_id,
        circuit,
        slots,
        domain_run.Reading(slot_index=slot.slot_index),
        seq=before + 1,
        agents=None,
        settings=None,
        now=now,
    )
    await write_intervention(
        session,
        org_id,
        circuit,
        action=REDO_STATION,
        actor=actor,
        before=before,
        now=now,
        slot_id=slot_id,
    )
    await announcements.circuit_changed(session, org_id, circuit_id, name=announcements.STATION_REDONE)
    return await read_circuit(session, org_id, circuit_id)


async def jump_to(
    session: AsyncSession,
    org_id: uuid.UUID,
    circuit_id: uuid.UUID,
    *,
    slot_id: uuid.UUID,
    agents: RoomAgents,
    actor: Actor,
    now: datetime,
) -> CircuitRead:
    """Move the circuit to a station out of order, from its reading period.

    Either mode may need this: a candidate arrives late, a station's equipment
    fails, the order has to change. Stations passed over are marked skipped
    rather than left looking scheduled — they are not coming.
    """
    circuit = await live_for_update(session, org_id, circuit_id)
    slot = await repository.slot_by_id(session, org_id, slot_id)
    if slot is None or slot.circuit_id != circuit_id:
        raise errors.SlotNotFound()

    slots = await repository.slots_for_circuit(session, org_id, circuit_id)
    try:
        domain_run.ensure_jump_target(slot.slot_index, slot_count=len(slots))
    except domain.InvalidCircuit as exc:
        raise_mapped(exc, _REFUSALS)

    before = circuit.phase_seq
    await service_steps.clear_patient(session, org_id, circuit, agents=agents, now=now, station_sat=False)
    await repository_run.mark_slots_skipped(
        session,
        org_id,
        circuit_id,
        before_index=slot.slot_index,
        statuses=[domain.SlotStatus.SCHEDULED, domain.SlotStatus.READING, domain.SlotStatus.IN_CONSULTATION],
    )
    slots = await repository.slots_for_circuit(session, org_id, circuit_id)
    await service_steps.apply_step(
        session,
        org_id,
        circuit,
        slots,
        domain_run.Reading(slot_index=slot.slot_index),
        seq=before + 1,
        agents=None,
        settings=None,
        now=now,
    )
    await write_intervention(
        session, org_id, circuit, action=JUMP_TO, actor=actor, before=before, now=now, slot_id=slot_id
    )
    await announcements.circuit_changed(session, org_id, circuit_id, name=announcements.JUMPED)
    return await read_circuit(session, org_id, circuit_id)
