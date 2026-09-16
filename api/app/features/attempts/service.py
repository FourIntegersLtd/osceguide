"""Attempt use cases, including the worker side of the contract."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import domain, errors, repository
from app.features.attempts.models import Attempt
from app.features.attempts.schemas import (
    AssessmentResultRead,
    AttemptRead,
    TranscriptIn,
    TranscriptMessageIn,
    TranscriptMessageRead,
    TranscriptRead,
    WorkerBootstrap,
)


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


# --- worker contract -------------------------------------------------------


async def bootstrap(session: AsyncSession, attempt_id: uuid.UUID) -> WorkerBootstrap:
    attempt = await _require(session, attempt_id)
    if not attempt.definition:
        # The worker refuses a job with no instructions, and would do so after
        # connecting. Failing here gives an error someone can act on.
        raise errors.AttemptNotReady()
    try:
        definition = domain.bootstrap_definition(attempt.definition)
    except domain.UnrenderableDefinition as exc:
        raise errors.AttemptNotReady(str(exc)) from exc

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
    seen = await repository.seen_message_ids(session, attempt_id)
    if not domain.should_store_chunk(message.message_id, seen):
        return
    await repository.add_chunk(
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

    existing = await repository.transcript_for(session, attempt_id)
    if not domain.should_accept_transcript(already_complete=bool(existing and existing.complete)):
        return

    seen = await repository.seen_message_ids(session, attempt_id)
    for message in transcript.messages:
        if domain.should_store_chunk(message.message_id, seen):
            await repository.add_chunk(
                session,
                attempt_id,
                message_id=message.message_id,
                seq=message.seq,
                role=message.role,
                message=message.message,
                spoken_at=message.timestamp,
            )
            seen.add(message.message_id)

    await repository.mark_transcript_complete(
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


# --- reads -----------------------------------------------------------------


async def read_attempt(
    session: AsyncSession, attempt_id: uuid.UUID, *, requester_id: uuid.UUID, is_admin: bool
) -> AttemptRead:
    attempt = await _require(session, attempt_id)
    _ensure_visible(attempt, requester_id=requester_id, is_admin=is_admin)
    return _attempt_read(attempt)


async def read_transcript(
    session: AsyncSession, attempt_id: uuid.UUID, *, requester_id: uuid.UUID, is_admin: bool
) -> TranscriptRead:
    attempt = await _require(session, attempt_id)
    _ensure_visible(attempt, requester_id=requester_id, is_admin=is_admin)
    record = await repository.transcript_for(session, attempt_id)
    rows = await repository.chunks_for(session, attempt_id)
    return TranscriptRead(
        attempt_id=attempt_id,
        complete=bool(record and record.complete),
        messages=[
            TranscriptMessageRead(role=r.role, message=r.message, seq=r.seq, spoken_at=r.spoken_at)
            for r in rows
        ],
    )


async def read_results(
    session: AsyncSession, attempt_id: uuid.UUID, *, requester_id: uuid.UUID, is_admin: bool
) -> list[AssessmentResultRead]:
    attempt = await _require(session, attempt_id)
    _ensure_visible(attempt, requester_id=requester_id, is_admin=is_admin)
    return [
        AssessmentResultRead(
            framework_id=r.framework_id,
            policy_version=r.policy_version,
            model_used=r.model_used,
            payload=dict(r.payload),
            scored_at=r.scored_at,
        )
        for r in await repository.results_for(session, attempt_id)
    ]


def _ensure_visible(attempt: Attempt, *, requester_id: uuid.UUID, is_admin: bool) -> None:
    if attempt.user_id != requester_id and not is_admin:
        raise errors.AttemptNotYours()


def _attempt_read(attempt: Attempt) -> AttemptRead:
    return AttemptRead(
        id=attempt.id,
        kind=attempt.kind,
        status=attempt.status,
        exam_id=attempt.exam_id,
        station_version_id=attempt.station_version_id,
        room_name=attempt.room_name,
        started_at=attempt.started_at,
        completed_at=attempt.completed_at,
        created_at=attempt.created_at,
    )
