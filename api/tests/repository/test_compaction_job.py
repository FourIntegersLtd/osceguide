"""The compaction job: which transcripts it takes, and what a failure does to the rest."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import jobs
from app.features.attempts import repository_transcript as transcripts
from app.features.attempts.service_compaction import CompactionFailed, compact_ready_transcripts
from tests.support.transcripts import add_turns, an_attempt, row_count

pytestmark = pytest.mark.db


def opener(session: AsyncSession):  # type: ignore[no-untyped-def]
    @asynccontextmanager
    async def open_session():  # type: ignore[no-untyped-def]
        yield session

    return open_session


async def delivered(session: AsyncSession, *, age: timedelta, turns: int = 3) -> uuid.UUID:
    attempt_id = await an_attempt(session)
    await add_turns(session, attempt_id, turns)
    await transcripts.mark_transcript_complete(
        session, attempt_id, runtime_label="livekit", at=datetime.now(UTC) - age
    )
    return attempt_id


async def test_ready_transcripts_compact_and_the_next_run_has_nothing_left(db_session: AsyncSession) -> None:
    old = await delivered(db_session, age=timedelta(hours=2))

    assert await compact_ready_transcripts(opener(db_session), limit=10) == 1

    assert await row_count(db_session, old) == 0
    assert await transcripts.chunk_count(db_session, old) == 3
    assert await compact_ready_transcripts(opener(db_session), limit=10) == 0


async def test_attempts_with_no_turns_at_the_head_of_the_batch_do_not_stall_the_job(
    db_session: AsyncSession,
) -> None:
    """An empty delivered transcript is `complete` too; it must not hog the newest-first batch."""
    empties = [await delivered(db_session, age=timedelta(hours=2, minutes=i), turns=0) for i in range(3)]
    compactable = await delivered(db_session, age=timedelta(hours=9))

    assert await compact_ready_transcripts(opener(db_session), limit=3) == 1

    assert await row_count(db_session, compactable) == 0
    assert await transcripts.chunk_count(db_session, compactable) == 3
    assert not any([await transcripts.is_compacted(db_session, empty) for empty in empties])


async def test_one_attempt_failing_still_compacts_the_others_then_fails_the_run(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    good_a = await delivered(db_session, age=timedelta(hours=2))
    bad = await delivered(db_session, age=timedelta(hours=3))
    good_b = await delivered(db_session, age=timedelta(hours=4))
    real = transcripts.compact

    async def flaky(session: AsyncSession, attempt_id: uuid.UUID) -> bool:
        if attempt_id == bad:
            raise RuntimeError("disk full")
        return await real(session, attempt_id)

    monkeypatch.setattr(transcripts, "compact", flaky)

    with pytest.raises(CompactionFailed, match="1 of 3"):
        await compact_ready_transcripts(opener(db_session), limit=10)

    assert await row_count(db_session, good_a) == 0
    assert await row_count(db_session, good_b) == 0
    assert await row_count(db_session, bad) == 3
    assert len(await transcripts.chunks_for(db_session, bad)) == 3


async def test_the_registered_task_runs_the_batch_and_staff_can_name_it(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    attempt_id = await delivered(db_session, age=timedelta(hours=2))
    monkeypatch.setattr("app.core.db.job_session", opener(db_session))

    await jobs.get_jobs_app().tasks["compact_transcripts"].func()

    assert await row_count(db_session, attempt_id) == 0
