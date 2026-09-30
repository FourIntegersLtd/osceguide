"""What the tutor is told about somebody, assembled from their own records.

The brief's shape is the engine's, and the rule the whole prompt rests on is
that nothing in it is invented — so these assert where each line came from.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import repository as attempts_repo
from app.features.attempts import repository_transcript as transcripts
from app.features.identity import repository as identity_repo
from app.features.tutor_memory import jobs, repository, service_brief
from tests.support.catalog import ensure_exam
from tests.support.rubrics import FULL_RUBRIC

pytestmark = pytest.mark.db

NOW = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)

# A mark under `tests.support.rubrics.FULL_RUBRIC` (R/A/G, upgraded from
# version 1), as the engine stores it. The brief reads it through that
# rubric's roles: an amber is the display's "fair", never a number.
RESULT_PAYLOAD = {
    "global_skills": {
        "structures_consultation": {"score": "A", "supporting_phrase": "Come back if it does not improve"},
    },
    "overall_score": 17,
}


async def a_user(db_session: AsyncSession, email: str) -> uuid.UUID:
    user = await identity_repo.create_user(
        db_session, email=email, name=email, password_hash=None, is_platform_admin=False
    )
    await db_session.flush()
    return user.id


async def test_an_empty_history_composes_an_empty_brief(db_session: AsyncSession) -> None:
    """The prompt has wording for this; what it must not get is an invented past."""
    user_id = await a_user(db_session, "brief-empty@example.com")

    brief = await service_brief.compose(db_session, user_id=user_id, now=NOW)

    assert brief["consultations"] == []
    assert brief["debriefs"] == []
    assert brief["last_conversation"] is None
    assert brief["facts"] == []
    assert brief["activity"] == []
    assert brief["tool_names"]["recall"] == "recall_history"


async def test_a_topic_they_opened_on_is_in_the_brief_and_the_greeting(db_session: AsyncSession) -> None:
    """The button they pressed is named back to them; an ordinary call has no topic."""
    from app.features.tutor_memory import service_session

    user_id = await a_user(db_session, "brief-topic@example.com")

    ordinary = await service_brief.compose(db_session, user_id=user_id, now=NOW)
    topic = {"title": "Asthma in adults?", "kind": "summary", "slug": "asthma"}
    on_topic = await service_brief.compose(db_session, user_id=user_id, now=NOW, topic=topic)

    assert ordinary["topic"] == {}
    assert on_topic["topic"] == {"title": "Asthma in adults?", "kind": "summary"}
    greeting = service_session.greeting_for(on_topic)
    assert greeting == "Hello. You wanted to talk about Asthma in adults. Where shall we start?"


async def test_a_marked_consultation_arrives_as_observations_not_scores(
    db_session: AsyncSession,
) -> None:
    user_id = await a_user(db_session, "brief-marked@example.com")
    exam = await ensure_exam(db_session, "sca", structure=FULL_RUBRIC)
    assert exam is not None
    attempt = await attempts_repo.create_attempt(
        db_session, kind="practice", user_id=user_id, exam_id=exam.id
    )
    await transcripts.save_result(
        db_session,
        attempt.id,
        framework_id="f",
        policy_version="v1",
        payload=RESULT_PAYLOAD,
        model_used="m",
        at=NOW,
    )

    brief = await service_brief.compose(db_session, user_id=user_id, now=NOW)

    assert len(brief["consultations"]) == 1
    consultation = brief["consultations"][0]
    assert consultation["domains"] == {"Global skills": "fair"}
    assert "overall_score" not in consultation
    assert consultation["days_ago"] == 0


async def test_an_unmarked_consultation_is_left_out(db_session: AsyncSession) -> None:
    """Asking "how did that go?" about one invites an answer the tutor cannot check."""
    user_id = await a_user(db_session, "brief-unmarked@example.com")
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    await attempts_repo.create_attempt(db_session, kind="practice", user_id=user_id, exam_id=exam.id)

    brief = await service_brief.compose(db_session, user_id=user_id, now=NOW)

    assert brief["consultations"] == []


async def test_the_last_conversation_carries_its_open_steps_only(db_session: AsyncSession) -> None:
    user_id = await a_user(db_session, "brief-last@example.com")
    await repository.add_note(
        db_session,
        user_id=user_id,
        exam_id=None,
        session_id=None,
        kind="session_summary",
        body={
            "summary": "We talked about follow-up timing.",
            "agreed_next_steps": [
                {"text": "Say one follow-up timeframe", "done": False},
                {"text": "Already done this", "done": True},
            ],
        },
    )

    brief = await service_brief.compose(db_session, user_id=user_id, now=NOW)

    assert brief["last_conversation"]["summary"] == "We talked about follow-up timing."
    assert brief["last_conversation"]["agreed_next_steps"] == ["Say one follow-up timeframe"]


async def test_activity_is_told_as_how_long_ago(db_session: AsyncSession) -> None:
    user_id = await a_user(db_session, "brief-activity@example.com")
    await repository.add_event(
        db_session,
        user_id=user_id,
        exam_id=None,
        kind="listened",
        ref_kind="podcast",
        ref_id="ep3",
        title="Safety netting, episode three",
        occurred_at=NOW - timedelta(days=12),
        meta=None,
    )

    brief = await service_brief.compose(db_session, user_id=user_id, now=NOW)

    assert brief["activity"] == [
        {"kind": "listened", "title": "Safety netting, episode three", "days_ago": 12}
    ]


async def test_a_finished_debrief_queues_its_own_summary(db_session: AsyncSession) -> None:
    """The seam `attempts` fires once a transcript is complete and marking is queued."""
    from sqlalchemy import text

    user_id = await a_user(db_session, "brief-seam@example.com")
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    source = await attempts_repo.create_attempt(db_session, kind="practice", user_id=user_id, exam_id=exam.id)
    debrief = await attempts_repo.create_attempt(
        db_session, kind="debrief", user_id=user_id, exam_id=exam.id, source_attempt_id=source.id
    )

    await jobs.on_interaction_complete(db_session, debrief)

    queued = await db_session.execute(
        text("SELECT task_name FROM procrastinate_jobs WHERE args->>'attempt_id' = :id"),
        {"id": str(debrief.id)},
    )
    assert list(queued.scalars()) == ["summarise_debrief"]


async def test_a_finished_consultation_queues_nothing(db_session: AsyncSession) -> None:
    from sqlalchemy import text

    user_id = await a_user(db_session, "brief-seam-practice@example.com")
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    attempt = await attempts_repo.create_attempt(
        db_session, kind="practice", user_id=user_id, exam_id=exam.id
    )

    await jobs.on_interaction_complete(db_session, attempt)

    queued = await db_session.execute(
        text("SELECT task_name FROM procrastinate_jobs WHERE args->>'attempt_id' = :id"),
        {"id": str(attempt.id)},
    )
    assert list(queued.scalars()) == []
