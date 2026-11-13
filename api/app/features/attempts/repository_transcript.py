"""Storage for an attempt's turns, its transcript record and its results."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import repository_nonverbal
from app.features.attempts.domain import Turn, from_document, to_document
from app.features.attempts.models import AssessmentResult, Transcript, TranscriptMessage


async def add_chunk(
    session: AsyncSession,
    attempt_id: uuid.UUID,
    *,
    message_id: str,
    seq: int,
    role: str,
    message: str,
    spoken_at: datetime,
) -> bool:
    """Store one spoken turn; False when this message id was already stored.

    The worker posts these best-effort, so repeats are expected. The unique constraint decides, in
    the insert itself, instead of a read of every stored id before each write.
    """
    stmt = (
        insert(TranscriptMessage)
        .values(
            attempt_id=attempt_id,
            message_id=message_id,
            seq=seq,
            role=role,
            message=message,
            spoken_at=spoken_at,
        )
        .on_conflict_do_nothing(constraint="uq_transcript_messages_attempt_message")
        .returning(TranscriptMessage.id)
    )
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def _document_for(session: AsyncSession, attempt_id: uuid.UUID) -> dict[str, Any] | None:
    """The compacted document, or `None` while the turns are still rows."""
    stmt = select(Transcript.messages).where(Transcript.attempt_id == attempt_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def chunks_for(session: AsyncSession, attempt_id: uuid.UUID) -> list[Turn]:
    """Every turn recorded so far, in the order they were spoken.

    Reads the rows first and the document only when there are none; callers cannot tell which.
    The order is the invariant. A reader holds no lock and each statement takes its own snapshot,
    so compaction can commit between the two. Compaction only ever deletes rows and a document is
    never removed, so rows-then-document always finds the turns in one home or the other.
    Document-then-rows reads "not yet", then finds the rows gone, and reports an empty transcript.
    """
    turns = await _row_turns(session, attempt_id)
    if turns:
        return turns
    document = await _document_for(session, attempt_id)
    return from_document(document) if document is not None else []


async def _row_turns(session: AsyncSession, attempt_id: uuid.UUID) -> list[Turn]:
    """The turns still stored as one row each, in the order they were spoken."""
    stmt = (
        select(
            TranscriptMessage.message_id,
            TranscriptMessage.seq,
            TranscriptMessage.role,
            TranscriptMessage.message,
            TranscriptMessage.spoken_at,
        )
        .where(TranscriptMessage.attempt_id == attempt_id)
        .order_by(TranscriptMessage.seq)
    )
    return [Turn(*row) for row in (await session.execute(stmt)).all()]


async def seen_message_ids(session: AsyncSession, attempt_id: uuid.UUID) -> set[str]:
    """Every message id already stored, for the late-turn log and the migration re-run.

    Rows first, then the document, for the reason `chunks_for` gives. The document branch is
    unreachable from the worker (`accept_chunk` and `accept_transcript` stop once compacted); it
    matters only on a migration re-run from `migration/load_attempts.py`, so keep it.
    """
    stmt = select(TranscriptMessage.message_id).where(TranscriptMessage.attempt_id == attempt_id)
    ids = set((await session.execute(stmt)).scalars())
    document = await _document_for(session, attempt_id)
    if document is not None:
        ids.update(turn.message_id for turn in from_document(document))
    return ids


async def transcript_for(session: AsyncSession, attempt_id: uuid.UUID) -> Transcript | None:
    """This attempt's delivery record, or `None` if the worker never finished delivering one."""
    stmt = select(Transcript).where(Transcript.attempt_id == attempt_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def transcripts_for(
    session: AsyncSession, attempt_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, Transcript]:
    """The delivery records for a page of attempts, keyed by attempt."""
    if not attempt_ids:
        return {}
    stmt = select(Transcript).where(Transcript.attempt_id.in_(list(attempt_ids)))
    return {transcript.attempt_id: transcript for transcript in (await session.execute(stmt)).scalars()}


async def chunk_count(session: AsyncSession, attempt_id: uuid.UUID) -> int:
    """How many turns have been stored for this attempt."""
    return (await chunk_counts_for(session, [attempt_id])).get(attempt_id, 0)


async def chunk_counts_for(session: AsyncSession, attempt_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, int]:
    """How many turns have been stored for each of a page of attempts, in two queries.

    The batched twin of `chunk_count`: the trial-attempt picker (rubrics plan
    §8, R-6) shows a turn count per row, and asking once per row would be the
    same N+1 `attempt_ids_with_results` exists to avoid. A compacted attempt
    answers from the plain `message_count` column, never the document. Rows are counted first,
    for the reason `chunks_for` gives.
    """
    if not attempt_ids:
        return {}
    ids = list(attempt_ids)
    rows = (
        select(TranscriptMessage.attempt_id, func.count())
        .where(TranscriptMessage.attempt_id.in_(ids))
        .group_by(TranscriptMessage.attempt_id)
    )
    counts = {attempt_id: count for attempt_id, count in (await session.execute(rows)).all()}
    compacted = select(Transcript.attempt_id, Transcript.message_count).where(
        Transcript.attempt_id.in_(ids), Transcript.message_count.is_not(None)
    )
    counts.update({attempt_id: count for attempt_id, count in (await session.execute(compacted)).all()})
    return counts


# --- compaction: a finished transcript's rows become one document (see jobs and the plan) ---

COMPACTION_GRACE = timedelta(hours=1)


async def lock_transcript(session: AsyncSession, attempt_id: uuid.UUID) -> None:
    """Serialise writers and the compactor for one attempt until the transaction ends.

    An advisory lock on the attempt id, so it works whether or not the `transcripts` row exists yet.
    """
    await session.execute(select(func.pg_advisory_xact_lock(func.hashtextextended(str(attempt_id), 0))))


async def is_compacted(session: AsyncSession, attempt_id: uuid.UUID) -> bool:
    """Whether this attempt's turns now live in its document rather than in rows.

    The one definition of "compacted": `Transcript.message_count IS NOT NULL`. `compact` writes it
    with the document in one statement and never for an attempt with no rows, so it is also
    always positive. An attempt with no turns stays uncompacted and still accepts a late chunk.
    """
    stmt = select(Transcript.message_count).where(Transcript.attempt_id == attempt_id)
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def compact(session: AsyncSession, attempt_id: uuid.UUID) -> bool:
    """Move this attempt's rows into `transcripts.messages`. `False` when there is nothing to do.

    One document write, then the rows go. No data is lost: `chunks_for` returns the same turns
    either side. An attempt with no rows, or no transcript record, is left untouched.
    """
    await lock_transcript(session, attempt_id)
    if await is_compacted(session, attempt_id):
        return False
    turns = await _row_turns(session, attempt_id)
    if not turns:
        return False
    updated = await session.execute(
        update(Transcript)
        .where(Transcript.attempt_id == attempt_id)
        .values(messages=to_document(turns), message_count=len(turns))
    )
    if updated.rowcount == 0:  # type: ignore[attr-defined]
        return False
    await session.execute(delete(TranscriptMessage).where(TranscriptMessage.attempt_id == attempt_id))
    return True


async def attempt_ids_ready_to_compact(session: AsyncSession, *, limit: int) -> list[uuid.UUID]:
    """Attempts whose transcript is complete, delivered over an hour ago and still rows. Newest first.

    The order is load-bearing: rows were inserted chronologically, so emptying the newest end
    leaves free pages at the tail of the heap, which a plain `VACUUM` can truncate back to the
    OS. Oldest-first would leave holes in the middle and the file would not shrink.

    Attempts with no rows are excluded in the query, not left to `compact`: it cannot mark them
    done (an empty document would make `is_compacted` true and drop a late chunk), so they would
    stay ready for ever and, being newest, fill every batch until nothing else was compacted.
    """
    has_rows = select(TranscriptMessage.id).where(TranscriptMessage.attempt_id == Transcript.attempt_id)
    stmt = (
        select(Transcript.attempt_id)
        .where(
            Transcript.complete.is_(True),
            Transcript.message_count.is_(None),
            Transcript.delivered_at < func.now() - COMPACTION_GRACE,
            has_rows.exists(),
        )
        .order_by(Transcript.delivered_at.desc())
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars())


async def mark_transcript_complete(
    session: AsyncSession, attempt_id: uuid.UUID, *, runtime_label: str | None, at: datetime
) -> Transcript:
    """Mark the delivery record complete, creating it on the first call and updating it after."""
    existing = await transcript_for(session, attempt_id)
    if existing is None:
        transcript = Transcript(
            attempt_id=attempt_id, complete=True, runtime_label=runtime_label, delivered_at=at
        )
        session.add(transcript)
        await session.flush()
        await session.refresh(transcript)
        return transcript
    await session.execute(
        update(Transcript)
        .where(Transcript.attempt_id == attempt_id)
        .values(complete=True, runtime_label=runtime_label, delivered_at=at)
    )
    return existing


# --- results ---


async def save_result(
    session: AsyncSession,
    attempt_id: uuid.UUID,
    *,
    framework_id: str,
    policy_version: str,
    payload: dict[str, Any],
    model_used: str | None,
    at: datetime,
) -> bool:
    """Store one scored result; False when this policy already has one for the attempt.

    Beside any earlier result under a different policy, never over it. A job retried after a crash
    scores again and finds its first result: the first one stands.
    """
    stmt = (
        insert(AssessmentResult)
        .values(
            attempt_id=attempt_id,
            framework_id=framework_id,
            policy_version=policy_version,
            payload=payload,
            model_used=model_used,
            scored_at=at,
        )
        .on_conflict_do_nothing(constraint="uq_assessment_results_attempt_policy")
        .returning(AssessmentResult.id)
    )
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def latest_results_by_attempt(
    session: AsyncSession, attempt_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, AssessmentResult]:
    """The newest result of each of these attempts, in one query. Attempts with none are absent."""
    if not attempt_ids:
        return {}
    stmt = (
        select(AssessmentResult)
        .where(AssessmentResult.attempt_id.in_(list(attempt_ids)))
        .distinct(AssessmentResult.attempt_id)
        .order_by(AssessmentResult.attempt_id, AssessmentResult.scored_at.desc())
    )
    return {result.attempt_id: result for result in (await session.execute(stmt)).scalars()}


async def results_for(session: AsyncSession, attempt_id: uuid.UUID) -> list[AssessmentResult]:
    """Every result this attempt has, oldest first, one per policy version it was scored under."""
    stmt = (
        select(AssessmentResult)
        .where(AssessmentResult.attempt_id == attempt_id)
        .order_by(AssessmentResult.scored_at)
    )
    return list((await session.execute(stmt)).scalars())


async def scored_policy_versions(session: AsyncSession, attempt_id: uuid.UUID) -> set[str]:
    """Every policy version this attempt has already been marked under, for `domain.should_score`."""
    stmt = select(AssessmentResult.policy_version).where(AssessmentResult.attempt_id == attempt_id)
    return set((await session.execute(stmt)).scalars())


async def erase_content_for_attempts(session: AsyncSession, attempt_ids: Sequence[uuid.UUID]) -> None:
    """Delete every transcript message, transcript record and mark for these
    attempts, for the account-erasure job (E-4). The attempts themselves are
    kept — an institution's roster history still needs to know a slot was
    sat — only the content a person spoke and the feedback it produced goes.
    """
    if not attempt_ids:
        return
    # The record first, then the rows: `compact` updates the record and then deletes the rows, so
    # taking them the other way round lets each wait on the other and Postgres aborts the batch.
    await session.execute(delete(Transcript).where(Transcript.attempt_id.in_(attempt_ids)))
    await session.execute(delete(TranscriptMessage).where(TranscriptMessage.attempt_id.in_(attempt_ids)))
    await repository_nonverbal.delete_all_for_attempts(session, attempt_ids)
    await session.execute(delete(AssessmentResult).where(AssessmentResult.attempt_id.in_(attempt_ids)))


async def attempt_ids_with_results(session: AsyncSession, attempt_ids: Sequence[uuid.UUID]) -> set[uuid.UUID]:
    """Which of these attempts have been marked, in one query.

    `recent_for_user` asks this per row, which is the N+1 every listing of
    attempts would otherwise repeat: a page of twenty attempts is twenty-one
    queries, and each of them loads whole payload documents to count them.
    """
    if not attempt_ids:
        return set()
    stmt = select(AssessmentResult.attempt_id).where(AssessmentResult.attempt_id.in_(list(attempt_ids)))
    return set((await session.execute(stmt)).scalars())


async def policy_versions_for(
    session: AsyncSession, attempt_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, list[str]]:
    """Which policy versions each of these attempts has been marked under."""
    if not attempt_ids:
        return {}
    stmt = (
        select(AssessmentResult.attempt_id, AssessmentResult.policy_version)
        .where(AssessmentResult.attempt_id.in_(list(attempt_ids)))
        .order_by(AssessmentResult.scored_at)
    )
    versions_by_attempt: dict[uuid.UUID, list[str]] = {}
    for attempt_id, version in (await session.execute(stmt)).all():
        versions_by_attempt.setdefault(attempt_id, []).append(version)
    return versions_by_attempt


async def erase_transcripts_for_attempts(session: AsyncSession, attempt_ids: Sequence[uuid.UUID]) -> None:
    """Delete only what a person said, for retention and an institution's deletion request.

    The marks (`AssessmentResult`) stay: the result ledger and the sitting report are built from
    them. `erase_content_for_attempts` is the account-erasure version that takes the marks too.
    """
    if not attempt_ids:
        return
    # The record first, then the rows, for the reason given there.
    await session.execute(delete(Transcript).where(Transcript.attempt_id.in_(attempt_ids)))
    await session.execute(delete(TranscriptMessage).where(TranscriptMessage.attempt_id.in_(attempt_ids)))
    await repository_nonverbal.delete_all_for_attempts(session, attempt_ids)
