"""A chunk racing the compaction job ends in the document or refused, never both and never lost.

Needs committed data and separate connections: the per-test rollback cannot show a lock held by one
transaction making another wait. Each test forces one ordering by holding a real lock from one
session until `pg_locks` shows the other waiting, not by sleeping. Only `lock_transcript` and the
row locks are contractual; nothing here depends on the order of calls inside the code under test.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session_factory, import_all_models
from app.features.attempts import repository, service_worker
from app.features.attempts import repository_transcript as transcripts
from app.features.attempts.models import Attempt, Transcript, TranscriptMessage
from app.features.attempts.schemas import TranscriptMessageIn
from app.features.catalog.models import Exam
from app.features.identity import repository as identity_repo
from app.features.identity.models import User
from tests.support.catalog import ensure_exam

pytestmark = pytest.mark.db

import_all_models()  # run alone, nothing else has registered the tables `attempts` points at

NOW = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)


@asynccontextmanager
async def committed_delivered_attempt() -> AsyncIterator[uuid.UUID]:
    """An attempt with two turns as rows and a transcript delivered two hours ago, removed afterwards."""
    factory = get_session_factory()
    async with factory() as session, session.begin():
        exam_count = await session.scalar(select(func.count()).select_from(Exam).where(Exam.code == "sca"))
        exam_existed = exam_count == 1
        user = await identity_repo.create_user(
            session, email=f"race-{uuid.uuid4().hex[:8]}@example.com", name="R", password_hash=None
        )
        exam = await ensure_exam(session, "sca")
        assert exam is not None
        attempt = await repository.create_attempt(session, kind="practice", user_id=user.id, exam_id=exam.id)
        for seq in range(2):
            await transcripts.add_chunk(
                session,
                attempt.id,
                message_id=f"m{seq}",
                seq=seq,
                role="assistant",
                message=f"turn {seq}",
                spoken_at=NOW,
            )
        await transcripts.mark_transcript_complete(
            session, attempt.id, runtime_label="livekit", at=datetime.now(UTC) - timedelta(hours=2)
        )
        attempt_id, user_id, exam_id = attempt.id, user.id, exam.id
    try:
        yield attempt_id
    finally:
        async with factory() as session, session.begin():
            await session.execute(delete(TranscriptMessage).where(TranscriptMessage.attempt_id == attempt_id))
            await session.execute(delete(Transcript).where(Transcript.attempt_id == attempt_id))
            await session.execute(delete(Attempt).where(Attempt.id == attempt_id))
            await session.execute(delete(User).where(User.id == user_id))
            if not exam_existed:
                await session.execute(delete(Exam).where(Exam.id == exam_id))


async def waiting_on(locktype: str) -> int:
    """How many connections are blocked on a lock of this type right now."""
    async with get_session_factory()() as session:
        return int(
            await session.scalar(
                text("SELECT count(*) FROM pg_locks WHERE locktype = :t AND NOT granted"), {"t": locktype}
            )
            or 0
        )


async def until_one_waits(locktype: str = "advisory") -> None:
    for _ in range(200):
        if await waiting_on(locktype) >= 1:
            return
        await asyncio.sleep(0.05)
    raise AssertionError(f"nothing ever waited on a {locktype} lock")


def late_turn() -> TranscriptMessageIn:
    return TranscriptMessageIn(role="assistant", message="late", timestamp=NOW, message_id="late", seq=5)


async def post_late_turn(attempt_id: uuid.UUID) -> None:
    async with get_session_factory()() as session, session.begin():
        await service_worker.accept_chunk(
            session, attempt_id, body_attempt_id=str(attempt_id), message=late_turn()
        )


async def compact_once(attempt_id: uuid.UUID) -> bool:
    async with get_session_factory()() as session, session.begin():
        return await transcripts.compact(session, attempt_id)


async def final_state(attempt_id: uuid.UUID) -> tuple[list[str], int]:
    """The ids `chunks_for` returns, and how many rows are left beside any document."""
    async with get_session_factory()() as session:
        ids = [turn.message_id for turn in await transcripts.chunks_for(session, attempt_id)]
        rows = await session.scalar(
            select(func.count())
            .select_from(TranscriptMessage)
            .where(TranscriptMessage.attempt_id == attempt_id)
        )
        return ids, int(rows or 0)


async def test_a_chunk_that_waits_for_compaction_is_refused() -> None:
    """The compactor holds the lock; the chunk queues behind it, then finds the document and drops."""
    async with committed_delivered_attempt() as attempt_id:
        compactor: AsyncSession = get_session_factory()()
        await compactor.begin()
        try:
            await transcripts.lock_transcript(compactor, attempt_id)
            writer = asyncio.create_task(post_late_turn(attempt_id))
            await until_one_waits()
            assert await transcripts.compact(compactor, attempt_id) is True
            await compactor.commit()
        finally:
            await compactor.close()
        await asyncio.wait_for(writer, timeout=10)

        assert await final_state(attempt_id) == (["m0", "m1"], 0)


async def test_a_chunk_that_holds_the_lock_first_is_kept_by_the_compaction() -> None:
    """The writer holds the lock when compaction starts; compaction waits, then folds the new turn in."""
    async with committed_delivered_attempt() as attempt_id:
        writer: AsyncSession = get_session_factory()()
        await writer.begin()
        try:
            await transcripts.lock_transcript(writer, attempt_id)
            compaction = asyncio.create_task(compact_once(attempt_id))
            await until_one_waits()
            await service_worker.accept_chunk(
                writer, attempt_id, body_attempt_id=str(attempt_id), message=late_turn()
            )
            await writer.commit()
        finally:
            await writer.close()

        assert await asyncio.wait_for(compaction, timeout=10) is True
        assert await final_state(attempt_id) == (["m0", "m1", "late"], 0)


async def read_turn_ids(session: AsyncSession, attempt_id: uuid.UUID) -> list[str]:
    return [turn.message_id for turn in await transcripts.chunks_for(session, attempt_id)]


async def read_counted(session: AsyncSession, attempt_id: uuid.UUID) -> list[str]:
    return ["m0", "m1"][: (await transcripts.chunk_counts_for(session, [attempt_id])).get(attempt_id, 0)]


async def read_seen(session: AsyncSession, attempt_id: uuid.UUID) -> list[str]:
    return sorted(await transcripts.seen_message_ids(session, attempt_id))


@pytest.mark.parametrize("read", [read_turn_ids, read_counted, read_seen], ids=["turns", "counts", "seen"])
async def test_a_reader_never_sees_neither_home_when_compaction_commits_mid_read(
    read: Callable[[AsyncSession, uuid.UUID], Awaitable[list[str]]],
) -> None:
    """READ COMMITTED gives each statement a fresh snapshot and a reader holds no lock.

    Compaction commits right after the reader's first statement: whichever home that statement
    looked in, the reader must still find the turns in the other. A reader that looks at the
    document first sees it empty, then finds the rows already gone, and reports no transcript.
    """
    async with committed_delivered_attempt() as attempt_id:
        reader: AsyncSession = get_session_factory()()
        real_execute = reader.execute
        interleaved = False

        async def execute_then_compact(*args, **kwargs):  # type: ignore[no-untyped-def]
            nonlocal interleaved
            result = await real_execute(*args, **kwargs)
            if not interleaved:
                interleaved = True
                assert await compact_once(attempt_id) is True
            return result

        reader.execute = execute_then_compact  # type: ignore[method-assign]
        try:
            assert await read(reader, attempt_id) == ["m0", "m1"]
        finally:
            await reader.close()
        assert interleaved


async def test_erasure_and_compaction_of_one_attempt_do_not_deadlock() -> None:
    """The compactor has updated the transcript record and not yet deleted the rows when erasure runs.

    Erasure must not take the rows' locks before the record's, or each waits on the other and
    Postgres aborts one: the whole erasure batch, which defers an account that is due for deletion.
    """
    async with committed_delivered_attempt() as attempt_id:
        compactor: AsyncSession = get_session_factory()()
        await compactor.begin()
        try:
            await transcripts.lock_transcript(compactor, attempt_id)
            await compactor.execute(
                update(Transcript).where(Transcript.attempt_id == attempt_id).values(message_count=2)
            )

            async def erase() -> None:
                async with get_session_factory()() as session, session.begin():
                    await transcripts.erase_content_for_attempts(session, [attempt_id])

            erasure = asyncio.create_task(erase())
            await until_one_waits("transactionid")
            await compactor.execute(
                delete(TranscriptMessage).where(TranscriptMessage.attempt_id == attempt_id)
            )
            await compactor.commit()
        finally:
            await compactor.close()
        await asyncio.wait_for(erasure, timeout=10)

        assert await final_state(attempt_id) == ([], 0)
        async with get_session_factory()() as session:
            assert await transcripts.transcript_for(session, attempt_id) is None
