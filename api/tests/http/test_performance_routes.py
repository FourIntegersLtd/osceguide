"""How somebody is doing, for the charts on the consumer exam dashboard."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import repository as attempts_repo
from app.features.attempts import repository_transcript as transcripts
from app.features.attempts.domain import Status
from app.features.catalog.models import Exam
from app.features.identity import repository as identity_repo
from tests.support.catalog import ensure_exam
from tests.support.rubrics import FULL_RUBRIC
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

URL = "/api/v1/me/performance"
SAT_AT = datetime(2026, 1, 1, tzinfo=UTC)

# The engine's document for one consultation, as `performance.py` reads it:
# marks under the rubric's own domain ids, prose beside them.
GREEN: dict[str, Any] = {
    "global_skills": {
        "structures_consultation": {"score": "G"},
        "avoids_repetition": {"score": "G"},
    },
    "tasks": {"discovers_ice": {"score": "G"}},
    "actionable_feedback": ["Keep going."],
}
RED: dict[str, Any] = {
    "global_skills": {
        "structures_consultation": {"score": "R"},
        "avoids_repetition": {"score": "R"},
    },
    "tasks": {"discovers_ice": {"score": "R"}},
    "actionable_feedback": ["Start again."],
}


async def a_learner(db_session: AsyncSession, make_actor, email: str) -> tuple[str, uuid.UUID]:  # type: ignore[no-untyped-def]
    token = await make_actor(email)
    user = await identity_repo.user_by_email(db_session, email)
    assert user is not None
    return token, user.id


async def an_attempt(
    db_session: AsyncSession,
    user_id: uuid.UUID,
    exam: Exam,
    *,
    sat_at: datetime,
    payload: dict[str, Any] | None = None,
) -> uuid.UUID:
    """One attempt, marked unless there is nothing to mark it with.

    `created_at` is written by hand because a test runs inside one
    transaction, and Postgres gives every row in it the same `now()` — the
    trend is ordered by it, so without this the order would be arbitrary.
    """
    attempt = await attempts_repo.create_attempt(
        db_session, kind="practice", user_id=user_id, exam_id=exam.id
    )
    attempt.created_at = sat_at
    if payload is None:
        return attempt.id
    await attempts_repo.set_status(db_session, attempt.id, status=Status.EVALUATED, at=sat_at)
    await transcripts.save_result(
        db_session,
        attempt.id,
        framework_id=str(exam.rubric_version_id),
        policy_version="platform-default@1",
        payload=payload,
        model_used="gpt-5-mini",
        at=sat_at,
    )
    await db_session.flush()
    return attempt.id


async def test_performance_needs_a_token(client: AsyncClient) -> None:
    response = await client.get(URL)
    assert response.status_code == 401


async def test_nothing_attempted_is_an_empty_answer(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """A new account has no exam to report on and no results to report.

    `exam_code` is null rather than an empty string: there is no exam here, and
    an empty string would be a code.
    """
    token = await make_actor("perf-new@example.com")
    response = await client.get(URL, headers=bearer(token))
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "exam_code": None,
        "summary": {"pass_rate": 0.0, "fail_rate": 0.0, "critical_rate": 0.0},
        "domains": [],
        "trend": [],
    }


async def test_an_exam_with_nothing_marked_yet_is_an_empty_answer(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """Sat but not marked is the dashboard's empty state, not a 404.

    A candidate who has just finished a consultation opens this screen while
    the marking is still running; a refusal would render as an error.
    """
    token, user_id = await a_learner(db_session, make_actor, "perf-unmarked@example.com")
    exam = await ensure_exam(db_session, "sca", structure=FULL_RUBRIC)
    await an_attempt(db_session, user_id, exam, sat_at=SAT_AT)

    body = (await client.get(URL, headers=bearer(token))).json()
    assert body["exam_code"] == "sca", "the exam is still named; only its results are missing"
    assert body["domains"] == []
    assert body["trend"] == []


async def test_an_exam_nobody_has_heard_of_is_refused(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """Naming an exam that does not exist is a client bug, not an empty state.

    The empty answer means "nothing marked yet at this exam", which is a thing
    the dashboard draws; a code nobody can sit is `unknown_exam`, the same
    refusal it gets everywhere else.
    """
    token, _ = await a_learner(db_session, make_actor, "perf-unknown@example.com")
    response = await client.get(URL, params={"exam_code": "not-an-exam"}, headers=bearer(token))
    assert response.status_code == 404
    assert response.json()["code"] == "unknown_exam"


async def test_the_charts_read_the_marking_back(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:
    """Domains, rates and a trend, from the engine's own documents.

    Two attempts, one all green and one all red: the domains average to an
    amber, half the attempts pass, and the red one is the critical. Read
    through the route rather than the service so the shape the frontend
    generates its types from is the thing asserted.
    """
    token, user_id = await a_learner(db_session, make_actor, "perf-marked@example.com")
    exam = await ensure_exam(db_session, "sca", structure=FULL_RUBRIC)
    await an_attempt(db_session, user_id, exam, sat_at=SAT_AT, payload=RED)
    await an_attempt(db_session, user_id, exam, sat_at=SAT_AT + timedelta(days=2), payload=GREEN)

    body = (await client.get(URL, params={"exam_code": "sca"}, headers=bearer(token))).json()

    assert body["exam_code"] == "sca"
    assert body["summary"] == {"pass_rate": 0.5, "fail_rate": 0.5, "critical_rate": 0.5}
    assert body["domains"] == [
        {"id": "global_skills", "label": "Global skills", "score": 66.5},
        {"id": "tasks", "label": "Tasks", "score": 66.5},
    ]
    assert [point["score"] for point in body["trend"]] == [33.0, 100.0], "oldest first"
    assert body["trend"][0]["date"].startswith("2026-01-01")


async def test_the_default_exam_is_the_one_last_attempted(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:
    """No `exam_code` means the exam this person is working on now.

    Somebody preparing for two exams should not have to name one to see the
    screen they just came from.
    """
    token, user_id = await a_learner(db_session, make_actor, "perf-default@example.com")
    sca = await ensure_exam(db_session, "sca", structure=FULL_RUBRIC)
    plab = await ensure_exam(db_session, "plab", structure=FULL_RUBRIC)
    await an_attempt(db_session, user_id, sca, sat_at=SAT_AT, payload=GREEN)
    await an_attempt(db_session, user_id, plab, sat_at=SAT_AT + timedelta(days=1), payload=RED)

    body = (await client.get(URL, headers=bearer(token))).json()
    assert body["exam_code"] == "plab"
    assert [point["score"] for point in body["trend"]] == [33.0], "only that exam's attempts"


async def test_performance_is_only_your_own(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:
    """One person's marks never appear on another's chart.

    Asserted here as well as in `attempts` because this route reads results the
    caller never names: it finds the attempts itself.
    """
    _, user_id = await a_learner(db_session, make_actor, "perf-mine@example.com")
    exam = await ensure_exam(db_session, "sca", structure=FULL_RUBRIC)
    await an_attempt(db_session, user_id, exam, sat_at=SAT_AT, payload=GREEN)

    other = await make_actor("perf-theirs@example.com")
    body = (await client.get(URL, params={"exam_code": "sca"}, headers=bearer(other))).json()
    assert body["trend"] == []
    assert body["domains"] == []
