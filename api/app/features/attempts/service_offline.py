"""Marking a consultation that no worker ran.

Every other attempt is delivered by the patient worker: it bootstraps, streams
its turns and posts the transcript. A peer session has no worker in the room —
it is two people — so its transcript arrives whole, after the fact, recovered
from a recording.

This is the door that path comes through, so the salvage cannot skip a step the
worker's delivery takes: the rubric is frozen first (without it the marking
refuses and logs `attempt_not_rendered`), then the turns, then the one call
that sets the status, queues the marking and notifies.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import errors, repository
from app.features.attempts import repository_transcript as transcripts
from app.features.attempts.service_render import render_definition
from app.features.attempts.service_worker import complete_interaction


async def mark_delivered_transcript(
    session: AsyncSession,
    attempt_id: uuid.UUID,
    *,
    turns: Sequence[Mapping[str, str]],
    runtime_label: str,
    now: datetime,
) -> None:
    """Attach a whole transcript to an attempt and put it through marking.

    `turns` are `{"role", "message"}` in the order they were spoken, with the
    candidate's turns as `doctor` — the role this slice already reads as the
    candidate elsewhere, so nothing needs translating at this boundary.
    """
    attempt = await repository.attempt_by_id(session, attempt_id)
    if attempt is None:
        raise errors.AttemptNotFound()
    await render_definition(session, attempt, now=now)
    for seq, turn in enumerate(turns):
        await transcripts.add_chunk(
            session,
            attempt.id,
            message_id=f"{runtime_label}:{attempt.id}:{seq}",
            seq=seq,
            role=turn["role"],
            message=turn["message"],
            spoken_at=now,
        )
    await transcripts.mark_transcript_complete(session, attempt.id, runtime_label=runtime_label, at=now)
    await complete_interaction(session, attempt, now=now)
