"""Starting a debrief from a consultation owned by the learner."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import domain, errors, repository, repository_transcript
from app.features.attempts.schemas import AttemptRead
from app.features.attempts.service_reads import _attempt_read, _ensure_visible, _require


async def start_debrief_attempt(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    source_attempt_id: uuid.UUID,
    now: datetime,
    standalone: bool = False,
) -> AttemptRead:
    """Create a debrief for an attempt the learner already owns.

    A debrief is a discussion of a source attempt, not another station sit.
    Re-running the entitlement gate here made the feedback page refuse a
    debrief after a trial user had spent their final station, even though the
    source attempt and feedback were already theirs.
    """
    source = await _require(session, source_attempt_id)
    _ensure_visible(source, requester_id=user_id, is_admin=False)
    if standalone and source.kind not in {"practice", "self_practice"}:
        raise errors.AttemptNotReady("Start this debrief from its practice session.")
    if not domain.is_reviewable(domain.Status(source.status)):
        raise errors.AttemptNotFinished()
    if source.kind == "debrief" or not await repository_transcript.chunk_count(session, source.id):
        raise errors.AttemptNotReady("A debrief needs a recorded consultation.")
    attempt = await repository.create_attempt(
        session,
        kind="debrief",
        user_id=user_id,
        exam_id=source.exam_id,
        org_id=source.org_id,
        station_version_id=source.station_version_id,
        source_attempt_id=source.id,
    )
    return _attempt_read(attempt)


async def debrief_sources(
    session: AsyncSession,
    user_id: uuid.UUID,
    attempt_ids: list[uuid.UUID],
) -> dict[uuid.UUID, uuid.UUID]:
    return await repository.sources_for(session, user_id, attempt_ids)


async def debrief_attempt_ids_about(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    source_attempt_id: uuid.UUID | None = None,
    station_version_id: uuid.UUID | None = None,
    set_entry_id: uuid.UUID | None = None,
) -> list[uuid.UUID]:
    """Ids of this person's debrief attempts about a consultation matching every filter given."""
    return await repository.debrief_ids_about(
        session,
        user_id,
        source_attempt_id=source_attempt_id,
        station_version_id=station_version_id,
        set_entry_id=set_entry_id,
    )
