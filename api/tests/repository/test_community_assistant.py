"""The assistant answers one public question when it is asked and the model has an answer."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import jobs
from app.core.audience import PUBLIC
from app.core.events import PENDING_KEY, user_topic
from app.features.community import repository, service
from app.features.community.models import Post
from app.features.identity import repository as identity_repository

pytestmark = pytest.mark.db


async def a_question(db_session: AsyncSession, author_id: Any, *, category: str) -> Post:
    return await repository.create_post(
        db_session,
        kind="question",
        author_id=author_id,
        title="Where is Settings?",
        body="Where do I change my password?",
        audience=PUBLIC,
        category=category,
    )


async def a_world(db_session: AsyncSession) -> Any:
    user = await identity_repository.create_user(
        db_session, email="asker@example.com", name="Asker", password_hash=None
    )
    return user.id


async def draft(title: str, body: str) -> str | None:
    return f"Open Settings, then Security. ({title})"


async def _quiet(title: str, body: str) -> str | None:
    return None


async def test_a_general_question_gets_one_assistant_reply_and_the_asker_is_told(
    db_session: AsyncSession,
) -> None:
    asker = await a_world(db_session)
    question = await a_question(db_session, asker, category="general")
    db_session.info.pop(PENDING_KEY, None)

    posted = await service.reply_as_assistant(db_session, question.id, draft=draft)
    again = await service.reply_as_assistant(db_session, question.id, draft=draft)

    replies = await repository.list_children(db_session, question.id)
    assert (posted, again) == (True, False)
    assert [(r.body, r.is_assistant, r.author_id, r.category) for r in replies] == [
        ("Open Settings, then Security. (Where is Settings?)", True, None, "general")
    ]
    assert db_session.info[PENDING_KEY] == [
        (
            user_topic(asker),
            "community_reply",
            {"post_id": str(question.id), "reply_id": str(replies[0].id)},
        )
    ]


async def test_a_public_question_in_any_category_gets_a_reply_when_the_drafter_has_text(
    db_session: AsyncSession,
) -> None:
    asker = await a_world(db_session)
    exam = await a_question(db_session, asker, category="exam")
    skills = await a_question(db_session, asker, category="skills")

    assert await service.reply_as_assistant(db_session, exam.id, draft=draft) is True
    assert await service.reply_as_assistant(db_session, skills.id, draft=draft) is True
    assert [r.body for r in await repository.list_children(db_session, exam.id)] == [
        "Open Settings, then Security. (Where is Settings?)"
    ]
    assert len(await repository.list_children(db_session, skills.id)) == 1


async def test_a_drafter_that_returns_none_posts_nothing_and_does_not_fail(db_session: AsyncSession) -> None:
    asker = await a_world(db_session)
    question = await a_question(db_session, asker, category="exam")
    db_session.info.pop(PENDING_KEY, None)

    posted = await service.reply_as_assistant(db_session, question.id, draft=_quiet)

    assert posted is False
    assert await repository.list_children(db_session, question.id) == []
    assert PENDING_KEY not in db_session.info


async def test_a_question_someone_has_answered_is_left_alone(db_session: AsyncSession) -> None:
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

    assert await service.reply_as_assistant(db_session, answered.id, draft=draft) is False
    assert [r.body for r in await repository.list_children(db_session, answered.id)] == ["Human answer."]


async def test_the_job_answers_the_post_it_is_given(db_session: AsyncSession, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    asker = await a_world(db_session)
    question = await a_question(db_session, asker, category="general")
    _stub(monkeypatch, db_session)

    await jobs.get_jobs_app().tasks["reply_as_assistant"].func(str(question.id))

    replies = await repository.list_children(db_session, question.id)
    assert [r.body for r in replies] == ["Open Settings, then Security. (Where is Settings?)"]


async def test_a_failing_draft_fails_the_run_and_posts_nothing(db_session: AsyncSession, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    asker = await a_world(db_session)
    question = await a_question(db_session, asker, category="general")
    _stub(monkeypatch, db_session, drafter=_exploding)

    with pytest.raises(RuntimeError, match="model down"):
        await jobs.get_jobs_app().tasks["reply_as_assistant"].func(str(question.id))

    assert await repository.list_children(db_session, question.id) == []


async def _exploding(title: str, body: str) -> str:
    raise RuntimeError("model down")


def _stub(monkeypatch, db_session: AsyncSession, drafter: Any = draft) -> None:  # type: ignore[no-untyped-def]
    @asynccontextmanager
    async def opener() -> AsyncIterator[AsyncSession]:
        yield db_session

    monkeypatch.setattr("app.core.db.job_session", opener)
    monkeypatch.setattr("app.features.community.jobs.draft_reply", lambda _settings: drafter)
