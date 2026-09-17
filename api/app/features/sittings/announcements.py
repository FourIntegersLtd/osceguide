"""Who to tell when a circuit changes.

A circuit change is watched from two sides at once: the supervisor running it
and every candidate waiting to be called. Both are told, because the trainee
portal's question — "is it my turn?" — is answered by exactly the events the
console causes, and a trainee is not subscribed to a circuit they cannot read.

Announcements are queued on the session and go out after the commit, so a
subscriber that re-reads the database sees the change it was told about. See
`core.events`.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import circuit_topic, publish_after_commit, user_topic
from app.features.sittings import repository

STARTED = "circuit.started"
TURN_SWITCHED = "circuit.turn_switched"
ENDED = "circuit.ended"
AGENT_DISPATCHED = "circuit.agent_dispatched"
CONSULTATION_ENDED = "circuit.consultation_ended"
TRAINEES_APPENDED = "circuit.trainees_appended"
REBUILT = "circuit.rebuilt"


async def circuit_changed(
    session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID, *, name: str
) -> None:
    """Tell the console and everybody rostered onto this circuit."""
    publish_after_commit(session, circuit_topic(circuit_id), name)
    for slot in await repository.slots_for_circuit(session, org_id, circuit_id):
        publish_after_commit(session, user_topic(slot.trainee_id), name)
