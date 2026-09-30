"""A person's practice record, over their whole marked history — not the
capped-100-attempt snapshot `achievementsFromAttempts.ts` used to compute in
the browser.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.http.test_performance_routes import GREEN, a_learner, an_attempt
from tests.support.catalog import ensure_exam
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

URL = "/api/v1/me/achievements"
DAY1 = datetime(2026, 9, 1, tzinfo=UTC)


async def test_achievements_needs_a_token(client: AsyncClient) -> None:
    response = await client.get(URL)
    assert response.status_code == 401


async def test_nothing_attempted_is_an_empty_answer(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("ach-new@example.com")
    response = await client.get(URL, headers=bearer(token))
    assert response.status_code == 200
    assert response.json() == {
        "station_count": 0,
        "current_streak": 0,
        "streak_badge_count": 0,
        "longest_streak": None,
    }


async def test_three_consecutive_marked_days_earn_one_badge(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    token, user_id = await a_learner(db_session, make_actor, "ach-streak@example.com")
    exam = await ensure_exam(db_session)
    for offset in range(3):
        await an_attempt(db_session, user_id, exam, sat_at=DAY1 + timedelta(days=offset), payload=GREEN)

    response = await client.get(URL, headers=bearer(token))
    assert response.status_code == 200
    body = response.json()
    assert body["streak_badge_count"] == 1
    assert body["longest_streak"] == {
        "length": 3,
        "start_date": "2026-09-01",
        "end_date": "2026-09-03",
    }


async def test_an_unmarked_attempt_does_not_count(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """A sat-but-not-yet-marked attempt is not a practice day — the same
    empty state `/me/performance` gives it."""
    token, user_id = await a_learner(db_session, make_actor, "ach-unmarked@example.com")
    exam = await ensure_exam(db_session)
    await an_attempt(db_session, user_id, exam, sat_at=DAY1, payload=None)

    response = await client.get(URL, headers=bearer(token))
    assert response.status_code == 200
    assert response.json()["longest_streak"] is None


async def test_a_gap_breaks_the_streak(client: AsyncClient, db_session: AsyncSession, make_actor) -> None:  # type: ignore[no-untyped-def]
    token, user_id = await a_learner(db_session, make_actor, "ach-gap@example.com")
    exam = await ensure_exam(db_session)
    await an_attempt(db_session, user_id, exam, sat_at=DAY1, payload=GREEN)
    await an_attempt(db_session, user_id, exam, sat_at=DAY1 + timedelta(days=5), payload=GREEN)

    response = await client.get(URL, headers=bearer(token))
    assert response.status_code == 200
    assert response.json()["longest_streak"]["length"] == 1
