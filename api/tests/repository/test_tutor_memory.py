"""What the tables guarantee, and what a delete can reach."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.identity import repository as identity_repo
from app.features.tutor_memory import repository
from app.features.tutor_memory.models import TutorNote
from tests.support.catalog import ensure_exam

pytestmark = pytest.mark.db

NOW = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)


async def a_user(db_session: AsyncSession, email: str) -> uuid.UUID:
    user = await identity_repo.create_user(
        db_session, email=email, name=email, password_hash=None, is_platform_admin=False
    )
    await db_session.flush()
    return user.id


async def test_a_delete_cannot_reach_somebody_elses_note(db_session: AsyncSession) -> None:
    """The user id is in the WHERE clause, not checked beforehand."""
    mine = await a_user(db_session, "repo-mine@example.com")
    theirs = await a_user(db_session, "repo-theirs@example.com")
    note = await repository.add_note(
        db_session, user_id=mine, exam_id=None, session_id=None, kind="stated_fact", body={"fact": "x"}
    )

    assert await repository.delete_note(db_session, theirs, note.id) == 0
    assert await db_session.get(TutorNote, note.id) is not None


async def test_forgetting_everything_leaves_other_people_alone(db_session: AsyncSession) -> None:
    mine = await a_user(db_session, "repo-sweep-mine@example.com")
    theirs = await a_user(db_session, "repo-sweep-theirs@example.com")
    for user_id in (mine, theirs):
        await repository.add_note(
            db_session,
            user_id=user_id,
            exam_id=None,
            session_id=None,
            kind="stated_fact",
            body={"fact": "x"},
        )

    counts = await repository.delete_all_for_user(db_session, mine, include_debriefs=False)

    assert counts == {"notes": 1, "events": 0, "debrief_summaries": 0}
    assert len(await repository.notes_of_kind(db_session, theirs, kind="stated_fact", limit=5)) == 1


async def test_a_note_of_an_invented_kind_is_refused(db_session: AsyncSession) -> None:
    user_id = await a_user(db_session, "repo-kind@example.com")
    with pytest.raises(IntegrityError):
        await repository.add_note(
            db_session,
            user_id=user_id,
            exam_id=None,
            session_id=None,
            kind="daydream",
            body={"fact": "x"},
        )


async def test_an_event_of_an_invented_kind_is_refused(db_session: AsyncSession) -> None:
    user_id = await a_user(db_session, "repo-event-kind@example.com")
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    with pytest.raises(IntegrityError):
        await repository.add_event(
            db_session,
            user_id=user_id,
            exam_id=exam.id,
            kind="absorbed",
            ref_kind="summary",
            ref_id="r",
            title="t",
            occurred_at=NOW,
            meta=None,
        )


async def test_the_most_recent_sighting_is_the_one_the_dedup_reads(db_session: AsyncSession) -> None:
    from datetime import timedelta

    user_id = await a_user(db_session, "repo-dedup@example.com")
    for offset in (0, 5, 2):
        await repository.add_event(
            db_session,
            user_id=user_id,
            exam_id=None,
            kind="viewed",
            ref_kind="summary",
            ref_id="anxiety",
            title="Anxiety",
            occurred_at=NOW + timedelta(hours=offset),
            meta=None,
        )

    assert await repository.last_seen_at(db_session, user_id, ref_kind="summary", ref_id="anxiety") == (
        NOW + timedelta(hours=5)
    )
