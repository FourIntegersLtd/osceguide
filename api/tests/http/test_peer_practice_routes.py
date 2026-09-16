"""Queueing, matching and practising."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog import repository as catalog_repo
from app.features.peer_practice import service
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def join(client: AsyncClient, token: str) -> dict:
    response = await client.post(
        "/api/v1/peer-practice/queue", json={"exam_code": "sca"}, headers=bearer(token)
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_joining_gives_a_place_in_the_queue(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("q1@example.com")
    status = await join(client, token)
    assert status["status"] == "waiting"
    assert status["position"] == 1


async def test_joining_twice_keeps_the_same_place(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Somebody tapping a button again, not an error worth refusing."""
    token = await make_actor("q2@example.com")
    first = await join(client, token)
    second = await join(client, token)
    assert first["entry_id"] == second["entry_id"]


async def test_position_reflects_who_arrived_first(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    first_token = await make_actor("q3-a@example.com")
    second_token = await make_actor("q3-b@example.com")
    await join(client, first_token)
    second = await join(client, second_token)
    assert second["position"] == 2
    assert second["waiting_count"] == 2


async def test_leaving_removes_you(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("q4@example.com")
    entry = await join(client, token)
    removed = await client.delete(f"/api/v1/peer-practice/queue/{entry['entry_id']}", headers=bearer(token))
    assert removed.status_code == 204

    status = await client.get(f"/api/v1/peer-practice/queue/{entry['entry_id']}", headers=bearer(token))
    assert status.json()["status"] == "left"


async def test_someone_elses_queue_entry_is_not_found(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("q5@example.com")
    entry = await join(client, token)
    stranger = await make_actor("q5-b@example.com")
    response = await client.get(f"/api/v1/peer-practice/queue/{entry['entry_id']}", headers=bearer(stranger))
    assert response.status_code == 404


async def test_two_waiting_people_are_matched(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    doctor_token = await make_actor("m1-a@example.com")
    patient_token = await make_actor("m1-b@example.com")
    first = await join(client, doctor_token)
    second = await join(client, patient_token)

    exam = await catalog_repo.exam_by_code(db_session, "sca")
    assert exam is not None
    matched = await service.match_waiting(db_session, exam.id)
    assert matched is not None
    await db_session.flush()

    for token, entry in ((doctor_token, first), (patient_token, second)):
        status = await client.get(f"/api/v1/peer-practice/queue/{entry['entry_id']}", headers=bearer(token))
        assert status.json()["status"] == "matched"
        assert status.json()["session_id"] == str(matched.id)


async def test_a_matched_pair_gets_opposite_roles_and_one_room(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    a_token = await make_actor("m2-a@example.com")
    b_token = await make_actor("m2-b@example.com")
    await join(client, a_token)
    await join(client, b_token)

    exam = await catalog_repo.exam_by_code(db_session, "sca")
    assert exam is not None
    matched = await service.match_waiting(db_session, exam.id)
    assert matched is not None
    await db_session.flush()

    a_view = await client.get(f"/api/v1/me/practice-sessions/{matched.id}", headers=bearer(a_token))
    b_view = await client.get(f"/api/v1/me/practice-sessions/{matched.id}", headers=bearer(b_token))
    assert {a_view.json()["my_role"], b_view.json()["my_role"]} == {"doctor", "patient"}
    assert a_view.json()["room_name"] == b_view.json()["room_name"]
    assert a_view.json()["room_name"] == f"practice_{matched.id}"


async def test_a_stranger_cannot_see_the_session(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    await join(client, await make_actor("m3-a@example.com"))
    await join(client, await make_actor("m3-b@example.com"))
    exam = await catalog_repo.exam_by_code(db_session, "sca")
    assert exam is not None
    matched = await service.match_waiting(db_session, exam.id)
    assert matched is not None
    await db_session.flush()

    stranger = await make_actor("m3-c@example.com")
    response = await client.get(f"/api/v1/me/practice-sessions/{matched.id}", headers=bearer(stranger))
    assert response.status_code == 404


async def test_a_session_can_be_ended_once(client: AsyncClient, make_actor, db_session: AsyncSession) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("m4-a@example.com")
    await join(client, token)
    await join(client, await make_actor("m4-b@example.com"))
    exam = await catalog_repo.exam_by_code(db_session, "sca")
    assert exam is not None
    matched = await service.match_waiting(db_session, exam.id)
    assert matched is not None
    await db_session.flush()

    url = f"/api/v1/me/practice-sessions/{matched.id}/end"
    first = await client.post(url, json={"reason": "finished"}, headers=bearer(token))
    assert first.json()["status"] == "ended"

    second = await client.post(url, json={}, headers=bearer(token))
    assert second.status_code == 409
    assert second.json()["code"] == "practice_session_ended"


async def test_one_person_waiting_is_not_matched(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    await join(client, await make_actor("m5@example.com"))
    exam = await catalog_repo.exam_by_code(db_session, "sca")
    assert exam is not None
    assert await service.match_waiting(db_session, exam.id) is None
