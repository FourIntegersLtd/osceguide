"""Many exam candidates at once: one circuit each, all or none."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.http.test_examiner_transcript_routes import an_examiner
from tests.http.test_sittings_routes import a_template_version
from tests.support.sittings import a_trainee, org_with_admin, published_station
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def _sitting(client: AsyncClient, admin: str, mode: str = "exam") -> str:
    template = await a_template_version(client, admin)
    created = await client.post(
        "/api/v1/orgs/kings/sittings",
        json={"name": "Finals", "programme_id": str(template), "mode": mode},
        headers=bearer(admin),
    )
    assert created.status_code == 201, created.text
    return created.json()["id"]


async def _circuit_count(client: AsyncClient, admin: str, sitting_id: str) -> int:
    response = await client.get(f"/api/v1/orgs/kings/sittings/{sitting_id}", headers=bearer(admin))
    assert response.status_code == 200, response.text
    return len(response.json()["circuits"])


def _url(sitting_id: str) -> str:
    return f"/api/v1/orgs/kings/sittings/{sitting_id}/circuits/bulk"


async def test_three_candidates_make_three_named_circuits(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting_id = await _sitting(client, admin)
    station = await published_station(client, admin, "kings", "S1")
    users = [await a_trainee(db_session, f"c{i}@example.com") for i in range(3)]

    response = await client.post(
        _url(sitting_id),
        json={"candidate_user_ids": [str(u) for u in users], "station_version_ids": [station]},
        headers=bearer(admin),
    )

    assert response.status_code == 201, response.text
    circuits = response.json()
    assert sorted(c["name"] for c in circuits) == [f"Exam – c{i}@example.com" for i in range(3)]
    assert {c["slots"][0]["trainee_id"] for c in circuits} == {str(u) for u in users}
    assert all(len(c["slots"]) == 1 and c["slots"][0]["station_version_id"] == station for c in circuits)
    assert await _circuit_count(client, admin, sitting_id) == 3


async def test_a_training_sitting_refuses_bulk_exam_circuits(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    sitting_id = await _sitting(client, admin, mode="training")
    station = await published_station(client, admin, "kings", "S1")
    user = await a_trainee(db_session, "a@example.com")

    response = await client.post(
        _url(sitting_id),
        json={"candidate_user_ids": [str(user)], "station_version_ids": [station]},
        headers=bearer(admin),
    )

    assert response.status_code == 409, response.text
    assert response.json()["code"] == "not_permitted_in_mode"


async def test_one_revoked_candidate_makes_no_circuits(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from app.features.roster import repository as roster_repo

    org_id, admin = await org_with_admin(client, make_actor)
    sitting_id = await _sitting(client, admin)
    station = await published_station(client, admin, "kings", "S1")
    users = [await a_trainee(db_session, f"c{i}@example.com") for i in range(3)]
    row = await roster_repo.trainee_by_email(db_session, org_id, "c2@example.com")
    assert row is not None
    revoked = await client.post(
        f"/api/v1/orgs/kings/trainees/{row.id}/access", json={"revoked": True}, headers=bearer(admin)
    )
    assert revoked.status_code == 200, revoked.text
    before = await _circuit_count(client, admin, sitting_id)

    response = await client.post(
        _url(sitting_id),
        json={"candidate_user_ids": [str(u) for u in users], "station_version_ids": [station]},
        headers=bearer(admin),
    )

    assert response.status_code == 409, response.text
    assert response.json()["code"] == "trainee_revoked"
    assert await _circuit_count(client, admin, sitting_id) == before == 0


async def test_thirteen_stations_is_an_invalid_circuit(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    sitting_id = await _sitting(client, admin)
    station = await published_station(client, admin, "kings", "S1")
    user = await a_trainee(db_session, "a@example.com")

    response = await client.post(
        _url(sitting_id),
        json={"candidate_user_ids": [str(user)], "station_version_ids": [station] * 13},
        headers=bearer(admin),
    )

    assert response.status_code == 409, response.text
    assert response.json()["code"] == "invalid_circuit"


async def test_duplicate_candidates_are_refused(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    sitting_id = await _sitting(client, admin)
    station = await published_station(client, admin, "kings", "S1")
    user = str(await a_trainee(db_session, "a@example.com"))

    response = await client.post(
        _url(sitting_id),
        json={"candidate_user_ids": [user, user], "station_version_ids": [station]},
        headers=bearer(admin),
    )

    assert response.status_code == 422, response.text


async def test_a_supervisor_cannot_bulk_create(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting_id = await _sitting(client, admin)
    station = await published_station(client, admin, "kings", "S1")
    user = await a_trainee(db_session, "a@example.com")
    _, supervisor_token = await an_examiner(db_session, org_id, "sup@example.com")

    response = await client.post(
        _url(sitting_id),
        json={"candidate_user_ids": [str(user)], "station_version_ids": [station]},
        headers=bearer(supervisor_token),
    )

    assert response.status_code == 403, response.text


async def test_an_unknown_sitting_is_not_found(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    station = await published_station(client, admin, "kings", "S1")
    user = await a_trainee(db_session, "a@example.com")

    response = await client.post(
        _url(str(uuid.uuid4())),
        json={"candidate_user_ids": [str(user)], "station_version_ids": [station]},
        headers=bearer(admin),
    )

    assert response.status_code == 404, response.text
