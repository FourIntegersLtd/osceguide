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

from app.core.ports import RoomAgents
from app.core.settings import Settings
from app.features.attempts import service as attempts_service
from app.features.sittings import domain, domain_run, errors, repository
from app.features.sittings.models import Circuit, Slot
from app.features.voice import service as voice


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
) -> None:
    """Take the patient out, and close off the station it was in.

    The room stays up and the candidate stays in it: only the patient leaves.
    """
    if circuit.room_name:
        await voice.clear_agents_from_room(agents=agents, room=circuit.room_name)
    if circuit.active_slot_id is not None and circuit.phase == domain_run.RunPhase.SIMULATION:
        await repository.update_slot(
            session,
            org_id,
            circuit.active_slot_id,
            status=domain.SlotStatus.COMPLETED,
            ended_at=now,
            exam_completed_at=now,
        )
