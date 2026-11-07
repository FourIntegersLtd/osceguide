"""Who is in the room: recording a no-show, and letting a dropped candidate back in.

Both are a person's judgement on exam day, so both need a reason, both are written to the circuit's
interventions and to the organisation's audit log, and neither touches the clock: a re-join sends the
patient back into the *same* station on the *same* deadline. More time is Add time's job.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.core.ports import RoomAgents
from app.core.settings import Settings
from app.features.attempts import service_reads as attempts_reads
from app.features.roster import service as roster
from app.features.sittings import (
    announcements,
    domain,
    domain_run,
    errors,
    repository,
    repository_run,
    service_rescue,
    service_run,
    service_steps,
)
from app.features.sittings.overrides import (
    ALLOW_REJOIN,
    MARK_ABSENT,
    Actor,
    live_for_update,
    write_intervention,
)
from app.features.sittings.schemas import CircuitRead, DispatchResult
from app.features.sittings.service import _require_circuit, read_circuit
from app.features.tenancy import service_audit as tenancy_audit


async def mark_absent(
    session: AsyncSession,
    org_id: uuid.UUID,
    circuit_id: uuid.UUID,
    *,
    trainee_id: uuid.UUID,
    agents: RoomAgents,
    actor: Actor,
    principal: Principal,
    now: datetime,
) -> CircuitRead:
    """Record that this person did not come: their unstarted stations become absent results (`skipped`).

    Refused once they have sat anything (a dropped connection is `allow_rejoin`'s case). When nobody
    is left to examine, the circuit ends, which is how an exam circuit of one candidate closes.
    """
    circuit = await _require_circuit(session, org_id, circuit_id, lock=True)
    if circuit.ended_at is not None:
        raise errors.CircuitNotLive()
    slots = await repository.slots_for_circuit_of_user(session, circuit_id, trainee_id)
    if not slots:
        raise errors.SlotNotFound()
    attempted = await attempts_reads.slots_with_attempts(session, [slot.id for slot in slots])
    if attempted or any(
        slot.status in (domain.SlotStatus.IN_CONSULTATION, domain.SlotStatus.COMPLETED) for slot in slots
    ):
        raise errors.CandidateAlreadySat()
    open_slots = [slot for slot in slots if slot.status in domain.UNSAT_SLOT_STATUSES]
    if not open_slots:
        return await read_circuit(session, org_id, circuit_id)  # already recorded: no second row

    before = circuit.phase_seq
    if circuit.active_slot_id in {slot.id for slot in open_slots}:
        await service_steps.clear_patient(session, org_id, circuit, agents=agents, now=now, station_sat=False)
    for slot in open_slots:
        await repository.update_slot(session, org_id, slot.id, status=domain.SlotStatus.SKIPPED, ended_at=now)
    await write_intervention(
        session,
        org_id,
        circuit,
        action=MARK_ABSENT,
        actor=actor,
        before=before,
        now=now,
        slot_id=slots[0].id,
        clock_moved=False,
    )
    name = (await roster.names_for_users(session, org_id, [trainee_id])).get(trainee_id) or "A candidate"
    await tenancy_audit.record_for_owner(
        session,
        org_id=org_id,
        actor=principal,
        action="circuit.candidate_marked_absent",
        target_type="circuit",
        target_id=str(circuit_id),
        summary=f"{name} marked absent from {circuit.name}: {actor.reason}",
        meta={"trainee_id": str(trainee_id), "slots": len(open_slots)},
    )
    remaining = await repository.slots_for_circuit(session, org_id, circuit_id)
    if not any(slot.status in domain.UNSAT_SLOT_STATUSES for slot in remaining):
        await service_run.end_circuit(session, org_id, circuit_id, agents=agents, now=now)
    await announcements.circuit_changed(session, org_id, circuit_id, name=announcements.ABSENT)
    return await read_circuit(session, org_id, circuit_id)


async def allow_rejoin(
    session: AsyncSession,
    org_id: uuid.UUID,
    circuit_id: uuid.UUID,
    *,
    agents: RoomAgents,
    settings: Settings,
    actor: Actor,
    principal: Principal,
    now: datetime,
) -> DispatchResult:
    """Let a candidate whose connection dropped back into the station they are sitting, once.

    Refused while the conversation is still running (nothing dropped), and for a second time on the
    same station. The deadline is left exactly where it was: the candidate loses the minutes they
    were away, unless the supervisor uses Add time.
    """
    circuit = await live_for_update(session, org_id, circuit_id)
    if circuit.phase != domain_run.RunPhase.SIMULATION or circuit.active_slot_id is None:
        raise errors.NoActiveStation()
    slot_id = circuit.active_slot_id
    live = (await attempts_reads.live_attempts_for_slots(session, [slot_id])).get(slot_id)
    if live is not None and live.status not in domain.CONNECTION_ENDED:
        raise errors.CandidateStillConnected()
    if await repository_run.slots_with_intervention(session, [slot_id], action=ALLOW_REJOIN):
        raise errors.RejoinAlreadyUsed()
    result = await service_rescue.resend_patient(
        session,
        org_id,
        circuit_id,
        agents=agents,
        settings=settings,
        actor=actor,
        now=now,
        action=ALLOW_REJOIN,
    )
    await tenancy_audit.record_for_owner(
        session,
        org_id=org_id,
        actor=principal,
        action="circuit.rejoin_allowed",
        target_type="circuit",
        target_id=str(circuit_id),
        summary=f"One re-join allowed on {circuit.name}: {actor.reason}",
        meta={"slot_id": str(slot_id)},
    )
    return result
