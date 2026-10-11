"""The assistant answers general and platform questions nobody has answered, and nothing else."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import jobs
from app.core.audience import PUBLIC
from app.core.settings import get_settings
from app.features.community import repository, service
from app.features.community.models import Post
from app.features.identity import repository as identity_repository

pytestmark = pytest.mark.db

NOW = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)
LONG_AGO = NOW - timedelta(hours=3)


async def a_question(
    db_session: AsyncSession, author_id: Any, *, category: str, age: timedelta = timedelta(hours=3)
) -> Post:
    question = await repository.create_post(
        db_session,
        kind="question",
        author_id=author_id,
        title="Where is Settings?",
        body="Where do I change my password?",
        audience=PUBLIC,
        category=category,
    )
    await db_session.execute(update(Post).where(Post.id == question.id).values(created_at=NOW - age))
    await db_session.flush()
    return question


async def a_world(db_session: AsyncSession) -> Any:
    user = await identity_repository.create_user(
        db_session, email="asker@example.com", name="Asker", password_hash=None
    )
    return user.id


async def draft(title: str, body: str) -> str:
    return f"Open Settings, then Security. ({title})"


async def test_a_general_question_gets_one_assistant_reply(db_session: AsyncSession) -> None:
    asker = await a_world(db_session)
    question = await a_question(db_session, asker, category="general")

    posted = await service.reply_as_assistant(db_session, draft=draft, now=NOW)
    again = await service.reply_as_assistant(db_session, draft=draft, now=NOW)

    replies = await repository.list_children(db_session, question.id)
    assert (posted, again) == (1, 0)
    assert [(r.body, r.is_assistant, r.author_id, r.category) for r in replies] == [
        ("Open Settings, then Security. (Where is Settings?)", True, None, "general")
    ]


async def test_exam_and_skills_questions_are_never_answered(db_session: AsyncSession) -> None:
    asker = await a_world(db_session)
    exam = await a_question(db_session, asker, category="exam")
    skills = await a_question(db_session, asker, category="skills")

    posted = await service.reply_as_assistant(db_session, draft=draft, now=NOW)

    assert posted == 0
    assert await repository.list_children(db_session, exam.id) == []
    assert await repository.list_children(db_session, skills.id) == []


async def test_a_question_someone_has_answered_or_is_too_new_is_left_alone(db_session: AsyncSession) -> None:
    asker = await a_world(db_session)
    answered = await a_question(db_session, asker, category="platform")
    await repository.create_post(
        db_session,
        kind="reply",
        author_id=asker,
        body="Human answer.",
        audience=PUBLIC,
        parent_id=answered.id,
    )
    fresh = await a_question(db_session, asker, category="general", age=timedelta(minutes=2))

    assert await service.reply_as_assistant(db_session, draft=draft, now=NOW) == 0
    assert await repository.list_children(db_session, fresh.id) == []


async def test_the_job_does_nothing_while_the_flag_is_off(db_session: AsyncSession, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    asker = await a_world(db_session)
    question = await a_question(db_session, asker, category="general")
    _stub(monkeypatch, db_session)
    monkeypatch.setattr(get_settings(), "community_assistant_replies", False)

    await jobs.get_jobs_app().tasks["reply_as_assistant"].func()

    assert await repository.list_children(db_session, question.id) == []


async def test_the_job_answers_a_general_post_when_the_flag_is_on(
    db_session: AsyncSession, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    asker = await a_world(db_session)
    question = await a_question(db_session, asker, category="general")
    _stub(monkeypatch, db_session)
    monkeypatch.setattr(get_settings(), "community_assistant_replies", True)

    await jobs.get_jobs_app().tasks["reply_as_assistant"].func()

    replies = await repository.list_children(db_session, question.id)
    assert [r.body for r in replies] == ["Open Settings, then Security. (Where is Settings?)"]


async def test_a_failing_draft_fails_the_run_and_posts_nothing(db_session: AsyncSession, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    asker = await a_world(db_session)
    question = await a_question(db_session, asker, category="general")
    _stub(monkeypatch, db_session, drafter=_exploding)
    monkeypatch.setattr(get_settings(), "community_assistant_replies", True)

    with pytest.raises(RuntimeError, match="model down"):
        await jobs.get_jobs_app().tasks["reply_as_assistant"].func()

    assert await repository.list_children(db_session, question.id) == []


async def _exploding(title: str, body: str) -> str:
    raise RuntimeError("model down")


def _stub(monkeypatch, db_session: AsyncSession, drafter: Any = draft) -> None:  # type: ignore[no-untyped-def]
    @asynccontextmanager
    async def opener() -> AsyncIterator[AsyncSession]:
        yield db_session

    monkeypatch.setattr("app.core.db.job_session", opener)
    monkeypatch.setattr("app.features.community.jobs.draft_reply", lambda _settings: drafter)
    monkeypatch.setattr("app.features.community.jobs.utcnow", lambda: NOW)
