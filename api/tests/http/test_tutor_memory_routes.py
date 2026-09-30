"""Recording what somebody did, reading what the tutor holds, and forgetting it."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.identity import repository as identity_repo
from app.features.tutor_memory import repository
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

NOW = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)


def an_event(**overrides: object) -> dict[str, object]:
    return {
        "kind": "viewed",
        "ref_kind": "summary",
        "ref_id": "anxiety",
        "title": "Anxiety, condition summary",
        **overrides,
    }


async def a_user(db_session: AsyncSession, make_actor, email: str) -> tuple[str, uuid.UUID]:  # type: ignore[no-untyped-def]
    token = await make_actor(email)
    user = await identity_repo.user_by_email(db_session, email)
    assert user is not None
    return token, user.id


async def test_activity_is_recorded(client: AsyncClient, db_session: AsyncSession, make_actor) -> None:  # type: ignore[no-untyped-def]
    token, user_id = await a_user(db_session, make_actor, "tm-record@example.com")

    response = await client.post("/api/v1/me/activity", json={"events": [an_event()]}, headers=bearer(token))

    assert response.status_code == 202, response.text
    assert response.json() == {"accepted": 1, "recorded": 1}
    assert len(await repository.recent_events(db_session, user_id, limit=10)) == 1


async def test_the_same_thing_twice_in_ten_minutes_is_one_visit(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    token, user_id = await a_user(db_session, make_actor, "tm-dedup@example.com")
    body = {
        "events": [
            an_event(occurred_at=NOW.isoformat()),
            an_event(occurred_at=(NOW + timedelta(minutes=3)).isoformat()),
        ]
    }

    response = await client.post("/api/v1/me/activity", json=body, headers=bearer(token))

    assert response.json() == {"accepted": 2, "recorded": 1}
    assert len(await repository.recent_events(db_session, user_id, limit=10)) == 1


async def test_coming_back_later_is_a_new_visit(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    token, user_id = await a_user(db_session, make_actor, "tm-later@example.com")
    body = {
        "events": [
            an_event(occurred_at=NOW.isoformat()),
            an_event(occurred_at=(NOW + timedelta(hours=2)).isoformat()),
        ]
    }

    await client.post("/api/v1/me/activity", json=body, headers=bearer(token))

    assert len(await repository.recent_events(db_session, user_id, limit=10)) == 2


async def test_a_nonsense_event_is_dropped_and_the_rest_of_the_batch_lands(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """These arrive as a tab is closing; refusing the batch would lose the good ones."""
    token, user_id = await a_user(db_session, make_actor, "tm-partial@example.com")
    body = {"events": [an_event(kind="telepathised"), an_event(ref_id="asthma")]}

    response = await client.post("/api/v1/me/activity", json=body, headers=bearer(token))

    assert response.status_code == 202
    assert response.json() == {"accepted": 2, "recorded": 1}
    stored = await repository.recent_events(db_session, user_id, limit=10)
    assert [e.ref_id for e in stored] == ["asthma"]


async def test_an_oversized_batch_is_refused(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("tm-huge@example.com")
    body = {"events": [an_event(ref_id=f"r{i}") for i in range(51)]}
    assert (await client.post("/api/v1/me/activity", json=body, headers=bearer(token))).status_code == 422


async def test_you_can_read_everything_the_tutor_holds(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """A memory nobody can inspect is one nobody can correct."""
    token, user_id = await a_user(db_session, make_actor, "tm-read@example.com")
    await client.post("/api/v1/me/activity", json={"events": [an_event()]}, headers=bearer(token))
    await repository.add_note(
        db_session,
        user_id=user_id,
        exam_id=None,
        session_id=None,
        kind="stated_fact",
        body={"fact": "Their exam is in six weeks"},
    )

    body = (await client.get("/api/v1/me/tutor-memory", headers=bearer(token))).json()

    assert [n["body"]["fact"] for n in body["notes"]] == ["Their exam is in six weeks"]
    assert [e["title"] for e in body["events"]] == ["Anxiety, condition summary"]
    assert body["debrief_summaries"] == []


async def test_you_see_nobody_elses_memory(client: AsyncClient, db_session: AsyncSession, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, mine = await a_user(db_session, make_actor, "tm-mine@example.com")
    theirs_token, _ = await a_user(db_session, make_actor, "tm-theirs@example.com")
    await repository.add_note(
        db_session,
        user_id=mine,
        exam_id=None,
        session_id=None,
        kind="stated_fact",
        body={"fact": "private"},
    )

    body = (await client.get("/api/v1/me/tutor-memory", headers=bearer(theirs_token))).json()

    assert body["notes"] == []


async def test_one_note_can_be_forgotten(client: AsyncClient, db_session: AsyncSession, make_actor) -> None:  # type: ignore[no-untyped-def]
    token, user_id = await a_user(db_session, make_actor, "tm-forget-one@example.com")
    note = await repository.add_note(
        db_session,
        user_id=user_id,
        exam_id=None,
        session_id=None,
        kind="stated_fact",
        body={"fact": "wrong"},
    )

    response = await client.delete(f"/api/v1/me/tutor-memory/notes/{note.id}", headers=bearer(token))

    assert response.status_code == 204
    assert await repository.notes_of_kind(db_session, user_id, kind="stated_fact", limit=5) == []


async def test_somebody_elses_note_is_a_404_not_a_403(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """Saying "that exists but is not yours" about a private note tells them it exists."""
    _, mine = await a_user(db_session, make_actor, "tm-owner@example.com")
    stranger, _ = await a_user(db_session, make_actor, "tm-stranger@example.com")
    note = await repository.add_note(
        db_session,
        user_id=mine,
        exam_id=None,
        session_id=None,
        kind="stated_fact",
        body={"fact": "private"},
    )

    response = await client.delete(f"/api/v1/me/tutor-memory/notes/{note.id}", headers=bearer(stranger))

    assert response.status_code == 404
    assert response.json()["code"] == "tutor_note_not_found"
    # That the row survived is asserted in tests/repository: a refused request
    # rolls this transaction back, so it cannot be seen from here.


async def test_forgetting_everything_says_how_much_went(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    token, user_id = await a_user(db_session, make_actor, "tm-forget-all@example.com")
    await client.post("/api/v1/me/activity", json={"events": [an_event()]}, headers=bearer(token))
    await repository.add_note(
        db_session,
        user_id=user_id,
        exam_id=None,
        session_id=None,
        kind="stated_fact",
        body={"fact": "x"},
    )

    response = await client.delete("/api/v1/me/tutor-memory", headers=bearer(token))

    assert response.status_code == 200
    assert response.json() == {"notes": 1, "events": 1, "debrief_summaries": 0}
    assert await repository.recent_events(db_session, user_id, limit=5) == []


async def test_these_routes_need_a_token(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/me/tutor-memory")).status_code == 401
    assert (await client.post("/api/v1/me/activity", json={"events": [an_event()]})).status_code == 401
