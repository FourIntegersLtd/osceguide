"""Putting the patient into the room, and taking it out again.

The two moments that make a station a recording — a conversation with LiveKit
and the worker that answers as the patient.

Removing the agent is how a consultation ends. The worker has no timer of its
own — it ends on the candidate leaving, the room closing, or being removed —
and on its way out it posts the full transcript, which queues the marking. So
"the bell goes" and "the recording is delivered" are the same act.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jobs import defer_in_transaction
from app.core.logging import get_logger
from app.core.ports import RoomAgents
from app.core.settings import Settings
from app.features.attempts import service as attempts_service
from app.features.roster import service as roster
from app.features.sittings import domain, domain_run, errors, repository
from app.features.sittings.models import Circuit, Slot
from app.features.voice import service as voice

log = get_logger(__name__)

CLEAR_ROOM_QUEUE = "circuits"
CLEAR_ROOM_TASK = "clear_room_agents"


async def dispatch_patient(
    session: AsyncSession,
    org_id: uuid.UUID,
    circuit: Circuit,
    slot: Slot,
    *,
    agents: RoomAgents,
    settings: Settings,
    now: datetime,
) -> tuple[uuid.UUID, str, int]:
    """Create the recording and put the patient into the room.

    Each dispatch creates a new attempt: the previous one is failed rather
    than overwritten, so a re-dispatch keeps the first recording rather than
    losing it.

    Returns `(attempt_id, agent_name, stale_agents_removed)`.
    """
    room = circuit.room_name
    if not room:
        raise errors.CircuitNotStarted()
    if await roster.is_revoked(session, org_id, slot.trainee_id):
        # R-8: revoked since the circuit was built. No recording, so nothing is marked.
        raise errors.TraineeRevokedError()

    attempt = await attempts_service.restart_for_slot(
        session,
        slot_id=slot.id,
        user_id=slot.trainee_id,
        org_id=org_id,
        station_version_id=slot.station_version_id,
        room_name=room,
        now=now,
    )
    agent_name, removed = await voice.dispatch_agent_into_room(
        agents=agents,
        settings=settings,
        room=room,
        attempt_id=attempt.id,
        candidate_ref=slot.trainee_id,
    )
    return attempt.id, agent_name, removed


async def clear_patient(
    session: AsyncSession,
    org_id: uuid.UUID,
    circuit: Circuit,
    *,
    agents: RoomAgents,
    now: datetime,
    station_sat: bool,
) -> bool:
    """Take the patient out, and close off the station it was in.

    The room stays up and the candidate stays in it: only the patient leaves.
    `station_sat` says what happened to the station: the bell went and it was
    sat (`completed`), or a human moved the circuit elsewhere (redo, jump) and
    it was abandoned part-way, so it goes back to `scheduled` and its partial
    recording is failed rather than marked as if it were a whole station (R-12).

    Taking the agent out is best-effort, so LiveKit being down never stops a
    circuit moving on. Returns whether it was taken out; a caller with nothing
    following it (ending the circuit) must arrange a retry, because no next
    dispatch will clear the room for it (R-13).
    """
    removed = True
    if circuit.room_name:
        try:
            await voice.clear_agents_from_room(agents=agents, room=circuit.room_name)
        except Exception:
            removed = False
            log.warning(
                "could not remove the patient from the room",
                circuit_id=str(circuit.id),
                room=circuit.room_name,
                exc_info=True,
            )
    if circuit.active_slot_id is None:
        return removed
    if not station_sat:
        await attempts_service.fail_live_for_slot(
            session, slot_id=circuit.active_slot_id, now=now, reason="interrupted"
        )
        for status in (domain.SlotStatus.READING, domain.SlotStatus.IN_CONSULTATION):
            await repository.update_slot(
                session,
                org_id,
                circuit.active_slot_id,
                only_if_status=status,
                status=domain.SlotStatus.SCHEDULED,
                ended_at=None,
            )
    elif circuit.phase == domain_run.RunPhase.SIMULATION:
        # Only a station that was sat: one skipped for a revoked candidate stays skipped.
        await repository.update_slot(
            session,
            org_id,
            circuit.active_slot_id,
            only_if_status=domain.SlotStatus.IN_CONSULTATION,
            status=domain.SlotStatus.COMPLETED,
            ended_at=now,
            exam_completed_at=now,
        )
    return removed


async def clear_patient_later(session: AsyncSession, circuit: Circuit) -> None:
    """Owe another go at taking the patient out of a room nothing else will clear (R-13).

    For an ended circuit only: a retry during a running one could remove the
    next station's patient. Written in the ending's transaction, and retried by
    the job until LiveKit answers, so "the circuit shows ended" and "the agent
    has left" stop being two different facts for longer than an outage.
    """
    if not circuit.room_name:
        return
    await defer_in_transaction(
        session,
        queue=CLEAR_ROOM_QUEUE,
        task=CLEAR_ROOM_TASK,
        args={"room": circuit.room_name, "circuit_id": str(circuit.id)},
        queueing_lock=f"clear_room:{circuit.room_name}",
        ignore_lock_conflict=True,
    )
