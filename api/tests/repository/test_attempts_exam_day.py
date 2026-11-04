"""Exam-day behaviour of the attempt engine: idempotent start, one chunk row, a server deadline."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.features.attempts import domain, repository, service, service_worker
from app.features.attempts import repository_transcript as transcripts
from app.features.attempts.models import Attempt, TranscriptMessage
from app.features.attempts.schemas import TranscriptMessageIn
from app.features.identity import repository as identity_repo
from tests.contract.test_worker_routes import DEFINITION
from tests.http.test_attempts_routes import entitle
from tests.support.catalog import ensure_exam
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

NOW = datetime(2026, 11, 4, 9, 0, tzinfo=UTC)


async def a_running_attempt(session: AsyncSession, *, started_at: datetime) -> tuple[uuid.UUID, int]:
    """A started practice attempt, and the seconds its deadline is after `started_at`."""
    user = await identity_repo.create_user(
        session, email=f"d{uuid.uuid4().hex[:8]}@example.com", name="D", password_hash=None
    )
    exam = await ensure_exam(session, "sca")
    attempt = await repository.create_attempt(session, kind="practice", user_id=user.id, exam_id=exam.id)
    await repository.freeze_definition(session, attempt.id, definition=DEFINITION, at=started_at)
    await repository.set_status(session, attempt.id, status=domain.Status.RUNNING, at=started_at)
    await session.flush()
    allowed = (
        exam.default_reading_seconds
        + exam.default_simulation_seconds
        + get_settings().attempt_deadline_grace_seconds
    )
    return attempt.id, allowed


def turn(message_id: str) -> TranscriptMessageIn:
    return TranscriptMessageIn(role="doctor", message="hello", timestamp=NOW, message_id=message_id, seq=0)


async def post(session: AsyncSession, attempt_id: uuid.UUID, message_id: str, at: datetime) -> None:
    await service_worker.accept_chunk(
        session, attempt_id, body_attempt_id=str(attempt_id), message=turn(message_id), now=at
    )


async def rows(session: AsyncSession, attempt_id: uuid.UUID) -> int:
    stmt = (
        select(func.count()).select_from(TranscriptMessage).where(TranscriptMessage.attempt_id == attempt_id)
    )
    return int(await session.scalar(stmt) or 0)


async def jobs(session: AsyncSession, attempt_id: uuid.UUID, task_like: str) -> int:
    stmt = text(
        "SELECT count(*) FROM procrastinate_jobs WHERE args->>'attempt_id' = :id AND task_name LIKE :t"
    )
    return int(await session.scalar(stmt, {"id": str(attempt_id), "t": task_like}) or 0)


async def test_two_starts_that_race_return_one_attempt(
    client: AsyncClient, make_actor, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    """Both requests passed the 'is there an unstarted attempt' read before either inserted."""
    from app.features.stations import repository as stations_repo

    token = await make_actor("racer@example.com")
    user = await identity_repo.user_by_email(db_session, "racer@example.com")
    exam = await ensure_exam(db_session, "sca")
    assert user is not None
    await entitle(db_session, user.id)
    station = await stations_repo.create_station(db_session, None, exam_id=exam.id, title="Racer")
    version = await stations_repo.add_version(
        db_session, None, station_id=station.id, version=1, content={"station_name": "Racer"}
    )
    await stations_repo.set_version_status(db_session, None, version.id, status="published", at=NOW, by=None)
    await db_session.flush()
    body = {"kind": "practice", "exam_code": "sca", "station_version_id": str(version.id)}
    first = await client.post("/api/v1/attempts", json=body, headers=bearer(token))

    real = repository.unstarted_attempt
    calls = {"n": 0}

    async def blind_once(*args, **kwargs):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        return None if calls["n"] == 1 else await real(*args, **kwargs)

    monkeypatch.setattr(repository, "unstarted_attempt", blind_once)
    second = await client.post("/api/v1/attempts", json=body, headers=bearer(token))

    assert second.status_code == 201, second.text
    assert second.json()["id"] == first.json()["id"]
    count = await db_session.scalar(
        select(func.count()).select_from(Attempt).where(Attempt.station_version_id == version.id)
    )
    assert count == 1


async def test_posting_a_chunk_twice_stores_one_row_and_queues_coverage_once(
    db_session: AsyncSession,
) -> None:
    attempt_id, _ = await a_running_attempt(db_session, started_at=NOW)
    await post(db_session, attempt_id, "m1", NOW + timedelta(seconds=5))
    await post(db_session, attempt_id, "m1", NOW + timedelta(seconds=6))
    assert await rows(db_session, attempt_id) == 1
    assert await jobs(db_session, attempt_id, "%coverage%") == 1


async def test_a_chunk_a_second_after_the_deadline_is_not_stored(db_session: AsyncSession) -> None:
    attempt_id, allowed = await a_running_attempt(db_session, started_at=NOW)
    await post(db_session, attempt_id, "on-time", NOW + timedelta(seconds=allowed - 1))
    await post(db_session, attempt_id, "late", NOW + timedelta(seconds=allowed + 1))
    assert [t.message_id for t in await transcripts.chunks_for(db_session, attempt_id)] == ["on-time"]


async def test_an_overdue_attempt_with_turns_is_marked_and_one_without_fails(
    db_session: AsyncSession,
) -> None:
    with_turns, allowed = await a_running_attempt(db_session, started_at=NOW)
    empty, _ = await a_running_attempt(db_session, started_at=NOW)
    in_time, _ = await a_running_attempt(db_session, started_at=NOW + timedelta(seconds=60))
    await post(db_session, with_turns, "m1", NOW + timedelta(seconds=5))

    closed = await service.abandon_stale_attempts(db_session, now=NOW + timedelta(seconds=allowed + 1))

    assert sorted(closed) == sorted([with_turns, empty])
    stmt = select(Attempt.id, Attempt.status, Attempt.failed_reason).where(
        Attempt.id.in_([with_turns, empty, in_time])
    )
    states = {row.id: (row.status, row.failed_reason) for row in (await db_session.execute(stmt)).all()}
    assert states[with_turns] == ("interaction_complete", None)
    assert states[empty] == ("failed", "abandoned")
    assert states[in_time] == ("running", None)
    assert await jobs(db_session, with_turns, "%scor%") == 1


def test_the_deadline_is_both_phases_plus_grace() -> None:
    assert domain.attempt_deadline(NOW, 120, 480, 30) == NOW + timedelta(seconds=630)


async def test_latest_scored_reads_fifty_attempts_in_a_handful_of_queries(db_session: AsyncSession) -> None:
    from sqlalchemy import event

    from app.features.attempts import service_feedback
    from tests.http.test_performance_routes import GREEN, an_attempt

    user = await identity_repo.create_user(db_session, email="many@example.com", name="M", password_hash=None)
    exam = await ensure_exam(db_session, "sca")
    ids = [
        await an_attempt(db_session, user.id, exam, sat_at=NOW + timedelta(minutes=i), payload=GREEN)
        for i in range(50)
    ]
    statements: list[str] = []

    def count(conn, cursor, statement, *args):  # type: ignore[no-untyped-def]
        statements.append(statement)

    sync_engine = db_session.bind.sync_engine  # type: ignore[union-attr]
    event.listen(sync_engine, "before_cursor_execute", count)
    try:
        scored = await service_feedback.latest_scored(db_session, ids)
    finally:
        event.remove(sync_engine, "before_cursor_execute", count)

    assert [s.attempt_id for s in scored] == ids
    assert len(statements) <= 6, statements
