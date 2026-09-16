"""The worker side of the attempt contract.

Split from `service.py` so the candidate-facing use cases and the machine-facing
ones can each be read on their own; they change for different reasons.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import domain, errors, repository
from app.features.attempts import repository_transcript as transcripts
from app.features.attempts.models import Attempt
from app.features.attempts.schemas import TranscriptIn, TranscriptMessageIn, WorkerBootstrap
from app.features.attempts.scoring import enqueue_scoring


async def _require(session: AsyncSession, attempt_id: uuid.UUID) -> Attempt:
    attempt = await repository.attempt_by_id(session, attempt_id)
    if attempt is None:
        raise errors.AttemptNotFound()
    return attempt


def _same_attempt(path_id: uuid.UUID, body_id: str) -> None:
    """A worker holds one attempt id and is given nothing else.

    A mismatch means a misrouted job or a bug, so it is refused rather than
    reconciled — writing the body's attempt instead would let one session's
    turns land on another's transcript.
    """
    if str(path_id) != body_id.strip():
        raise errors.AttemptMismatch()


async def bootstrap(
    session: AsyncSession, attempt_id: uuid.UUID, *, now: datetime | None = None
) -> WorkerBootstrap:
    """Hand the worker its attempt, and record that the session has started.

    A worker fetching this *is* the session beginning — it is the only signal we
    get, since nothing else reports a start. Without it the attempt stays
    `created`, and then the completed transcript cannot move it to
    `interaction_complete`, so the marking is never queued and the attempt sits
    unmarked with a full transcript behind it.
    """
    attempt = await _require(session, attempt_id)
    if not attempt.definition:
        # The worker refuses a job with no instructions, and would do so after
        # connecting. Failing here gives an error someone can act on.
        raise errors.AttemptNotReady()
    try:
        definition = domain.bootstrap_definition(attempt.definition)
    except domain.UnrenderableDefinition as exc:
        raise errors.AttemptNotReady(str(exc)) from exc

    if now is not None and domain.Status(attempt.status) is domain.Status.CREATED:
        await repository.set_status(session, attempt_id, status=str(domain.Status.RUNNING), at=now)

    scenario = dict(attempt.definition.get("scenario") or {}) or {
        "ref": attempt.definition.get("scenario_ref", {}),
        "title": "",
        "raw": {},
    }
    return WorkerBootstrap(
        attempt={
            "attempt_id": str(attempt.id),
            "definition": definition,
            "candidate_ref": str(attempt.user_id),
            "attempt_context": {},
            "started_at": attempt.started_at.isoformat() if attempt.started_at else None,
            "ended_at": attempt.completed_at.isoformat() if attempt.completed_at else None,
            "status": attempt.status,
        },
        scenario=scenario,
    )


async def accept_chunk(
    session: AsyncSession, attempt_id: uuid.UUID, *, body_attempt_id: str, message: TranscriptMessageIn
) -> None:
    _same_attempt(attempt_id, body_attempt_id)
    await _require(session, attempt_id)
    seen = await transcripts.seen_message_ids(session, attempt_id)
    if not domain.should_store_chunk(message.message_id, seen):
        return
    await transcripts.add_chunk(
        session,
        attempt_id,
        message_id=message.message_id,
        seq=message.seq,
        role=message.role,
        message=message.message,
        spoken_at=message.timestamp,
    )


async def accept_transcript(
    session: AsyncSession,
    attempt_id: uuid.UUID,
    *,
    body_attempt_id: str,
    transcript: TranscriptIn,
    now: datetime,
) -> None:
    """Record the delivered transcript and move the attempt on.

    The final transcript is the authority: chunks are best-effort and may have
    been dropped, so anything missing is filled in here rather than trusted to
    have arrived.
    """
    _same_attempt(attempt_id, body_attempt_id)
    attempt = await _require(session, attempt_id)

    existing = await transcripts.transcript_for(session, attempt_id)
    if not domain.should_accept_transcript(already_complete=bool(existing and existing.complete)):
        return

    seen = await transcripts.seen_message_ids(session, attempt_id)
    for message in transcript.messages:
        if domain.should_store_chunk(message.message_id, seen):
            await transcripts.add_chunk(
                session,
                attempt_id,
                message_id=message.message_id,
                seq=message.seq,
                role=message.role,
                message=message.message,
                spoken_at=message.timestamp,
            )
            seen.add(message.message_id)

    await transcripts.mark_transcript_complete(
        session, attempt_id, runtime_label=transcript.runtime_label, at=now
    )
    if domain.Status(attempt.status) is not domain.Status.INTERACTION_COMPLETE:
        target = domain.Status.INTERACTION_COMPLETE if transcript.complete else domain.Status.FAILED
        try:
            domain.transition(domain.Status(attempt.status), target)
        except domain.InvalidTransition:
            # A late delivery for an attempt already scored or failed: the
            # turns are kept, the status is not walked backwards.
            return
        await repository.set_status(
            session,
            attempt_id,
            status=str(target),
            at=now,
            reason=None if transcript.complete else "incomplete_transcript",
        )
        if target is domain.Status.INTERACTION_COMPLETE:
            # Enqueued in this transaction, so the work and the record of it
            # being owed commit together. b2c spawned a thread and b2b a daemon
            # thread, so a deploy mid-generation stranded the attempt forever.
            await enqueue_scoring(session, attempt, now=now)
