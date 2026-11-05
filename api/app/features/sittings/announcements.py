"""Who to tell when a circuit changes.

A circuit change is watched from three sides at once: the supervisor running
it, the organisation's exam-day board, and every candidate waiting to be
called. All three are told, because the trainee portal's question — "is it my
turn?" — is answered by exactly the events the clock causes, and a trainee is
not subscribed to a circuit they cannot read.

Announcements are queued on the session and go out after the commit, so a
subscriber that re-reads the database sees the change it was told about. See
`core.events`.
"""

from __future__ import annotations

import uuid
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import circuit_topic, org_topic, publish_after_commit, user_topic
from app.features.sittings import repository
from app.features.tenancy import service as tenancy

STARTED = "circuit.started"
ENDED = "circuit.ended"
# One name for every move the clock makes, because a subscriber re-reads the
# whole read model anyway: what changed is in the snapshot, not in the name.
PHASE_ADVANCED = "circuit.phase_advanced"
PAUSED = "circuit.paused"
RESUMED = "circuit.resumed"
CLOCK_CHANGED = "circuit.clock_changed"
PATIENT_RESENT = "circuit.patient_resent"
STATION_REDONE = "circuit.station_redone"
JUMPED = "circuit.jumped"
AUTO_ADVANCE_CHANGED = "circuit.auto_advance_changed"
TRAINEES_APPENDED = "circuit.trainees_appended"
REBUILT = "circuit.rebuilt"
# A candidate's attempt moved on (running, interaction complete, marked, failed): the clock did
# not cause it, so nothing else would tell the console or the board.
ATTEMPT_PROGRESS = "circuit.attempt_progress"
ABSENT = "circuit.candidate_absent"
# The name every attempt change goes out under on a person's own stream (`useMeEvents(["attempt"])`).
ATTEMPT_CHANGED = "attempt"


class SlotAttempt(Protocol):
    """The fields of an attempt that say which circuit it belongs to."""

    id: uuid.UUID
    org_id: uuid.UUID | None
    slot_id: uuid.UUID | None


async def circuit_changed(
    session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID, *, name: str
) -> None:
    """Tell the console, the organisation's board, and everybody rostered on.

    Three audiences for one event. The organisation's topic is what makes the
    exam-day board live without it subscribing to every circuit it is showing —
    an admin watching twelve candidates would otherwise hold twelve streams.
    """
    publish_after_commit(session, circuit_topic(circuit_id), name)
    publish_after_commit(session, org_topic(org_id), name)
    for slot in await repository.slots_for_circuit(session, org_id, circuit_id):
        publish_after_commit(session, user_topic(slot.trainee_id), name)


async def attempt_progress(session: AsyncSession, attempt: SlotAttempt) -> None:
    """Tell the console and the organisation's board that a slot's attempt changed status.

    Nothing to say for an attempt that is not on a slot: a practice attempt is nobody's circuit.
    """
    if attempt.slot_id is None or attempt.org_id is None:
        return
    slot = await repository.slot_by_id(session, attempt.org_id, attempt.slot_id)
    if slot is None:
        return
    publish_after_commit(session, circuit_topic(slot.circuit_id), ATTEMPT_PROGRESS)
    publish_after_commit(session, org_topic(attempt.org_id), ATTEMPT_PROGRESS)
    # The candidate's own screen is told by the caller. Reviewers read the same mark, so the
    # circuit's supervisor and the organisation's admins hear it on their own streams too.
    circuit = await repository.circuit_by_id(session, attempt.org_id, slot.circuit_id)
    reviewers = set(await tenancy.admin_user_ids(session, attempt.org_id))
    if circuit is not None and circuit.supervisor_user_id is not None:
        reviewers.add(circuit.supervisor_user_id)
    for reviewer in sorted(reviewers, key=str):
        publish_after_commit(session, user_topic(reviewer), ATTEMPT_CHANGED, {"attempt_id": str(attempt.id)})
