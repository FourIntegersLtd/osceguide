"""Storage for attempts, their turns and their results.

Attempts are not org-scoped in the usual way: a consumer attempt has no
organisation at all. The org-scoped reads say so in their names, and the
worker-facing reads take an attempt id because that is all a worker is given.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import encode_cursor
from app.features.attempts.models import AssessmentResult, Attempt, Transcript, TranscriptMessage


async def create_attempt(
    session: AsyncSession,
    *,
    kind: str,
    user_id: uuid.UUID,
    exam_id: uuid.UUID,
    org_id: uuid.UUID | None = None,
    station_version_id: uuid.UUID | None = None,
    slot_id: uuid.UUID | None = None,
    set_entry_id: uuid.UUID | None = None,
    peer_session_id: uuid.UUID | None = None,
    source_attempt_id: uuid.UUID | None = None,
    room_name: str | None = None,
) -> Attempt:
    attempt = Attempt(
        kind=kind,
        user_id=user_id,
        exam_id=exam_id,
        org_id=org_id,
        station_version_id=station_version_id,
        slot_id=slot_id,
        set_entry_id=set_entry_id,
        peer_session_id=peer_session_id,
        source_attempt_id=source_attempt_id,
        room_name=room_name,
    )
    session.add(attempt)
    await session.flush()
    await session.refresh(attempt)
    return attempt


async def attempt_by_id(session: AsyncSession, attempt_id: uuid.UUID) -> Attempt | None:
    return (await session.execute(select(Attempt).where(Attempt.id == attempt_id))).scalar_one_or_none()


async def live_attempt_for_slot(session: AsyncSession, slot_id: uuid.UUID) -> Attempt | None:
    stmt = select(Attempt).where(Attempt.slot_id == slot_id, Attempt.status != "failed")
    return (await session.execute(stmt)).scalar_one_or_none()


async def set_status(
    session: AsyncSession,
    attempt_id: uuid.UUID,
    *,
    status: str,
    at: datetime,
    reason: str | None = None,
) -> None:
    values: dict[str, Any] = {"status": status}
    if status == "running":
        values["started_at"] = at
    elif status == "interaction_complete":
        values["completed_at"] = at
    elif status == "failed":
        values["failed_reason"] = reason
    await session.execute(update(Attempt).where(Attempt.id == attempt_id).values(**values))


async def freeze_definition(
    session: AsyncSession, attempt_id: uuid.UUID, *, definition: dict[str, Any], at: datetime
) -> None:
    """Write the rendered definition once.

    Guarded on `definition IS NULL` in the statement itself rather than by a
    read-then-write, so two workers racing to bootstrap the same attempt cannot
    both believe they were first.
    """
    await session.execute(
        update(Attempt)
        .where(Attempt.id == attempt_id, Attempt.definition.is_(None))
        .values(definition=definition, definition_frozen_at=at)
    )


async def delete_attempt(session: AsyncSession, attempt_id: uuid.UUID) -> None:
    from sqlalchemy import delete

    await session.execute(delete(Attempt).where(Attempt.id == attempt_id))


# --- transcript ------------------------------------------------------------


async def add_chunk(
    session: AsyncSession,
    attempt_id: uuid.UUID,
    *,
    message_id: str,
    seq: int,
    role: str,
    message: str,
    spoken_at: datetime,
) -> TranscriptMessage:
    row = TranscriptMessage(
        attempt_id=attempt_id,
        message_id=message_id,
        seq=seq,
        role=role,
        message=message,
        spoken_at=spoken_at,
    )
    session.add(row)
    await session.flush()
    return row


async def chunks_for(session: AsyncSession, attempt_id: uuid.UUID) -> list[TranscriptMessage]:
    stmt = (
        select(TranscriptMessage)
        .where(TranscriptMessage.attempt_id == attempt_id)
        .order_by(TranscriptMessage.seq)
    )
    return list((await session.execute(stmt)).scalars())


async def seen_message_ids(session: AsyncSession, attempt_id: uuid.UUID) -> set[str]:
    stmt = select(TranscriptMessage.message_id).where(TranscriptMessage.attempt_id == attempt_id)
    return set((await session.execute(stmt)).scalars())


async def transcript_for(session: AsyncSession, attempt_id: uuid.UUID) -> Transcript | None:
    stmt = select(Transcript).where(Transcript.attempt_id == attempt_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def mark_transcript_complete(
    session: AsyncSession, attempt_id: uuid.UUID, *, runtime_label: str | None, at: datetime
) -> Transcript:
    existing = await transcript_for(session, attempt_id)
    if existing is None:
        row = Transcript(attempt_id=attempt_id, complete=True, runtime_label=runtime_label, delivered_at=at)
        session.add(row)
        await session.flush()
        await session.refresh(row)
        return row
    await session.execute(
        update(Transcript)
        .where(Transcript.attempt_id == attempt_id)
        .values(complete=True, runtime_label=runtime_label, delivered_at=at)
    )
    return existing


# --- results ---------------------------------------------------------------


async def save_result(
    session: AsyncSession,
    attempt_id: uuid.UUID,
    *,
    framework_id: str,
    policy_version: str,
    payload: dict[str, Any],
    model_used: str | None,
    at: datetime,
) -> AssessmentResult:
    row = AssessmentResult(
        attempt_id=attempt_id,
        framework_id=framework_id,
        policy_version=policy_version,
        payload=payload,
        model_used=model_used,
        scored_at=at,
    )
    session.add(row)
    await session.flush()
    return row


async def results_for(session: AsyncSession, attempt_id: uuid.UUID) -> list[AssessmentResult]:
    stmt = (
        select(AssessmentResult)
        .where(AssessmentResult.attempt_id == attempt_id)
        .order_by(AssessmentResult.scored_at)
    )
    return list((await session.execute(stmt)).scalars())


async def scored_policy_versions(session: AsyncSession, attempt_id: uuid.UUID) -> set[str]:
    stmt = select(AssessmentResult.policy_version).where(AssessmentResult.attempt_id == attempt_id)
    return set((await session.execute(stmt)).scalars())


async def list_for_user(
    session: AsyncSession, user_id: uuid.UUID, *, limit: int, cursor: dict[str, Any] | None = None
) -> tuple[list[Attempt], str | None]:
    stmt = select(Attempt).where(Attempt.user_id == user_id)
    if cursor:
        stmt = stmt.where(Attempt.created_at < datetime.fromisoformat(cursor["t"]))
    rows = list(
        (
            await session.execute(
                stmt.order_by(Attempt.created_at.desc(), Attempt.id.desc()).limit(limit + 1)
            )
        ).scalars()
    )
    if len(rows) <= limit:
        return rows, None
    page = rows[:limit]
    return page, encode_cursor({"t": page[-1].created_at, "i": str(page[-1].id)})
