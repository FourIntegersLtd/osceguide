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
from app.features.attempts.service import ensure_entitled_to_begin
from app.features.attempts.service_render import render_definition
from app.features.catalog import service as catalog
from app.features.station_sets import service as station_sets
from app.features.tutor_memory import jobs as tutor_jobs

log = get_logger(__name__)

# Which side of the conversation the AI plays. A debrief is the tutor talking
# the candidate through what happened; everything else is the patient.
_MODE_FOR_KIND = {"debrief": "tutor"}


async def _require(session: AsyncSession, attempt_id: uuid.UUID) -> Attempt:
    """Fetch the attempt a worker call names, or refuse if it does not exist."""
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
        try:
            await ensure_entitled_to_begin(session, attempt, now=now)
        except errors.NotEntitled as exc:
            # Not left `created` for a worker to retry into the same refusal for ever.
            await repository.set_status(
                session, attempt_id, status=domain.Status.FAILED, at=now, reason="not_entitled"
            )
            raise errors.NotEntitledToBegin(details=exc.details) from exc
        await repository.set_status(session, attempt_id, status=domain.Status.RUNNING, at=now)
        await _credit_practice_set_entry(session, attempt, at=now)

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


async def _entry_this_attempt_counts_against(
    session: AsyncSession, attempt: Attempt
) -> tuple[uuid.UUID, bool] | None:
    """Which practice-set entry, if any, this attempt is sat inside — and whether it is a debrief.

    A `set_station` attempt names its entry directly. A `debrief` attempt never does — the CHECK on
    `attempts` only lets it name the consultation it discusses — so its entry is found by following
    `source_attempt_id` back to that consultation. Anything else (`practice`, `self_practice`,
    `exam_slot`, `peer`) is not sat inside a practice set at all, and `None` says so.
    """
    if attempt.set_entry_id is not None:
        return attempt.set_entry_id, False
    if attempt.kind == "debrief" and attempt.source_attempt_id is not None:
        source = await repository.attempt_by_id(session, attempt.source_attempt_id)
        if source is not None and source.set_entry_id is not None:
            return source.set_entry_id, True
    return None


async def _credit_practice_set_entry(session: AsyncSession, attempt: Attempt, *, at: datetime) -> None:
    """Count this attempt against its practice-set entry's limit, now that it has started.

    `station_sets.start_entry_attempt` used to count an attempt the moment it was created — before
    the candidate had done anything but open the page — so a consultation nobody ever joined still
    used up a go. This is the point that is actually true: a worker fetching its attempt is the
    session beginning (see `bootstrap`'s docstring), so this is where the count belongs.

    Nothing to do for an attempt outside a practice set (`practice`, `exam_slot`, `peer`, and a
    debrief of one of those): the limit this slice enforces is `station_sets`' own, not a rule of
    every attempt.
    """
    target = await _entry_this_attempt_counts_against(session, attempt)
    if target is None:
        return
    set_entry_id, is_debrief = target
    exam = await catalog.exam_ref_by_id(session, attempt.exam_id)
    if exam is None:
        # The exam an attempt was created against cannot vanish — `exam_id` is a `RESTRICT` foreign
        # key — but nothing here is worth crashing the session over if it somehow did.
        log.warning("bootstrap.exam_missing", attempt_id=str(attempt.id), exam_id=str(attempt.exam_id))
        return
    counted = await station_sets.record_started_attempt(
        session,
        set_entry_id=set_entry_id,
        debrief=is_debrief,
        limit=exam.station_attempt_limit,
        at=at,
    )
    if not counted:
        # A race let two attempts against the same entry both reach this point before either had
        # counted, and the limit was already spent by the other one. `station_sets`' own route
        # refuses this far earlier in the common case; this is the same refusal, just discovered
        # later because nothing knew the limit was spent until now.
        raise errors.SetEntryAttemptLimitReached()


async def accept_chunk(
    session: AsyncSession, attempt_id: uuid.UUID, *, body_attempt_id: str, message: TranscriptMessageIn
) -> None:
    """Store one turn as it is spoken, and nudge live coverage if it was the candidate's."""
    _same_attempt(attempt_id, body_attempt_id)
    attempt = await _require(session, attempt_id)
    await transcripts.lock_transcript(session, attempt_id)
    if await transcripts.is_compacted(session, attempt_id):
        # The turns already live in the document, so storing this would leave a row beside it. For
        # a repeat that loses nothing; the final transcript this chunk would have preceded was
        # delivered long ago. A genuinely new turn is lost, though (a salvaged attempt had no final
        # delivery to cover it), so say so rather than look like a repeat.
        known = await transcripts.seen_message_ids(session, attempt_id)
        if domain.should_store_chunk(message.message_id, known):
            log.warning(
                "transcript.late_turn_dropped",
                attempt_id=str(attempt_id),
                message_id=message.message_id,
                seq=message.seq,
                role=message.role,
            )
        return
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
    await transcripts.lock_transcript(session, attempt_id)

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
