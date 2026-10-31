"""Attempts with transcript turns, for the tests of how a transcript is stored and compacted."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import repository
from app.features.attempts import repository_transcript as transcripts
from app.features.attempts.models import TranscriptMessage
from app.features.identity import repository as identity_repo
from tests.support.catalog import ensure_exam

TURNS_AT = datetime(2026, 10, 31, 12, 0, 0, 123456, tzinfo=UTC)


async def an_attempt(session: AsyncSession, email: str | None = None) -> uuid.UUID:
    user = await identity_repo.create_user(
        session, email=email or f"{uuid.uuid4().hex[:8]}@example.com", name="C", password_hash=None
    )
    exam = await ensure_exam(session, "sca")
    assert exam is not None, "the seed migration should have created the four exams"
    attempt = await repository.create_attempt(session, user_id=user.id, exam_id=exam.id, kind="practice")
    return attempt.id


async def add_turns(session: AsyncSession, attempt_id: uuid.UUID, count: int) -> None:
    for seq in range(count):
        await transcripts.add_chunk(
            session,
            attempt_id,
            message_id=f"m{seq}",
            seq=seq,
            role="doctor" if seq % 2 else "patient",
            message=f'turn {seq} "quoted"\ncafé',
            spoken_at=TURNS_AT + timedelta(microseconds=seq),
        )


async def row_count(session: AsyncSession, attempt_id: uuid.UUID) -> int:
    return int(
        await session.scalar(
            select(func.count())
            .select_from(TranscriptMessage)
            .where(TranscriptMessage.attempt_id == attempt_id)
        )
        or 0
    )
