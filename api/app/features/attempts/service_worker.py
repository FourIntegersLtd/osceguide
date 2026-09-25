"""The worker side of the attempt contract."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.features.attempts import domain, domain_definition, errors, repository
from app.features.attempts import repository_transcript as transcripts
from app.features.attempts.jobs import enqueue_scoring
from app.features.attempts.jobs_coverage import enqueue_coverage
from app.features.attempts.models import Attempt
from app.features.attempts.schemas import TranscriptIn, TranscriptMessageIn, WorkerBootstrap
from app.features.attempts.service_render import render_definition
from app.features.tutor_memory import jobs as tutor_jobs

log = get_logger(__name__)

# Which side of the conversation the AI plays. A debrief is the tutor talking
# the candidate through what happened; everything else is the patient.
_MODE_FOR_KIND = {"debrief": "tutor"}


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


def _snapshot_time(attempt: Attempt) -> datetime:
    """When a render with no clock supplied is stamped.

    The created time rather than `now()`: a definition describes the attempt it
    belongs to, and two renders of the same attempt should not differ only by
    when somebody asked.
    """
    return attempt.created_at


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

    frozen_definition = attempt.definition
    if not frozen_definition:
        # Nothing frozen yet, so this is the first bootstrap: render now.
        frozen_definition = await render_definition(session, attempt, now=now or _snapshot_time(attempt))
    try:
        definition = domain_definition.bootstrap_definition(frozen_definition)
    except domain.UnrenderableDefinition as exc:
        raise errors.AttemptNotReady(str(exc)) from exc

    if now is not None and domain.Status(attempt.status) is domain.Status.CREATED:
        await repository.set_status(session, attempt_id, status=domain.Status.RUNNING, at=now)

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
        scenario=domain_definition.worker_scenario(frozen_definition),
    )


async def accept_chunk(
    session: AsyncSession, attempt_id: uuid.UUID, *, body_attempt_id: str, message: TranscriptMessageIn
) -> None:
    _same_attempt(attempt_id, body_attempt_id)
    attempt = await _require(session, attempt_id)
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
    if message.role in {"user", "doctor", "candidate"}:
        await enqueue_coverage(session, attempt)


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
        if target is domain.Status.INTERACTION_COMPLETE:
            await complete_interaction(session, attempt, now=now)
        else:
            await repository.set_status(
                session, attempt_id, status=target, at=now, reason="incomplete_transcript"
            )


async def complete_interaction(session: AsyncSession, attempt: Attempt, *, now: datetime) -> None:
    """The consultation is over: record it, queue the marking, tell whoever listens.

    One function for the two ways it happens — the worker delivering the
    transcript, and support salvaging one the worker never finished — so the
    salvage cannot forget a step the delivery takes.
    """
    await repository.set_status(session, attempt.id, status=domain.Status.INTERACTION_COMPLETE, at=now)
    # Enqueued in this transaction, so the work and the record of it being
    # owed commit together. b2c spawned a thread and b2b a daemon thread, so a
    # deploy mid-generation stranded the attempt forever.
    await enqueue_scoring(session, attempt, now=now)
    await enqueue_coverage(session, attempt)
    # After the marking is queued, in the same transaction, so a debrief
    # summary lands with it or not at all.
    await tutor_jobs.on_interaction_complete(session, attempt)
