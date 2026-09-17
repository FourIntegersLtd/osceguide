"""The screens an institution runs, each in one request.

These are the read models the frontend is waiting on: the console replaces a
session read, a station list, a trainee list, a staff list and one feedback
probe per slot, repeated every eight seconds, and the trainee portal replaces
two lists polled every five.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from tests.http.test_sittings_routes import (
    a_template_version,
    org_with_admin,
    published_station,
)
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def a_user(db_session: AsyncSession, email: str) -> uuid.UUID:
    from app.features.identity import repository as identity_repo

    user = await identity_repo.user_by_email(db_session, email)
    if user is None:
        user = await identity_repo.create_user(
            session=db_session, email=email, name=email, password_hash=None
        )
        await db_session.flush()
    return user.id


async def a_circuit(
    client: AsyncClient,
    admin: str,
    slug: str,
    *,
    sitting_id: str,
    trainee_ids: list[str],
    station_version_ids: list[str],
    supervisor_user_id: str | None = None,
) -> dict:
    body: dict = {
        "name": "Circuit A",
        "trainee_ids": trainee_ids,
        "station_version_ids": station_version_ids,
    }
    if supervisor_user_id:
        body["supervisor_user_id"] = supervisor_user_id
    created = await client.post(
        f"/api/v1/orgs/{slug}/sittings/{sitting_id}/circuits", json=body, headers=bearer(admin)
    )
    assert created.status_code == 201, created.text
    return created.json()


async def a_sitting(client: AsyncClient, admin: str, slug: str, *, mode: str = "exam") -> dict:
    template_version = await a_template_version(client, admin, slug)
    created = await client.post(
        f"/api/v1/orgs/{slug}/sittings",
        json={
            "name": "Finals",
            "feedback_template_version_id": str(template_version),
            "mode": mode,
        },
        headers=bearer(admin),
    )
    assert created.status_code == 201, created.text
    return created.json()


# --- the org dashboard -----------------------------------------------------


async def test_the_org_dashboard_counts_without_listing(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Five requests, four of them lists fetched only to be counted."""
    org_id, admin = await org_with_admin(client, make_actor)
    await a_sitting(client, admin, "kings")
    await published_station(client, admin, "kings", "Chest pain")
    await client.post(
        "/api/v1/orgs/kings/trainees",
        json={"email": "t1@example.com", "first_name": "Ada"},
        headers=bearer(admin),
    )

    response = await client.get("/api/v1/orgs/kings/dashboard", headers=bearer(admin))
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["slug"] == "kings"
    assert body["counts"] == {
        "trainees": 1,
        "stations": 1,
        "staff": 1,
        "published_feedback_templates": 1,
        "sittings": 1,
    }
    assert body["setup"]["ready_to_run"] is True
    assert [s["name"] for s in body["recent_sittings"]] == ["Finals"]


async def test_an_empty_org_is_told_what_it_is_missing(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor, slug="empty")
    body = (await client.get("/api/v1/orgs/empty/dashboard", headers=bearer(admin))).json()
    assert body["setup"] == {
        "trainees_added": False,
        "stations_authored": False,
        "team_invited": True,
        "feedback_template_published": False,
        "ready_to_run": False,
    }


async def test_the_org_dashboard_is_refused_to_outsiders(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    await org_with_admin(client, make_actor)
    stranger = await make_actor("stranger@example.com")
    response = await client.get("/api/v1/orgs/kings/dashboard", headers=bearer(stranger))
    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"


# --- the supervisor's list -------------------------------------------------


async def test_a_supervisor_sees_only_the_circuits_they_are_named_on(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings")
    station = await published_station(client, admin, "kings", "S1")
    supervisor_id = await a_user(db_session, "sup@example.com")
    supervisor = await make_actor(
        "sup2@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="supervisor"),),
        active_org_slug="kings",
    )
    mine = await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(await a_user(db_session, "cand1@example.com"))],
        station_version_ids=[station],
        supervisor_user_id=str(supervisor_id),
    )
    await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(await a_user(db_session, "cand2@example.com"))],
        station_version_ids=[station],
    )

    for_supervisor = await client.get(
        "/api/v1/orgs/kings/supervisor/circuits",
        headers=bearer(await _token_for(make_actor, org_id, supervisor_id)),
    )
    assert for_supervisor.status_code == 200, for_supervisor.text
    items = for_supervisor.json()["items"]
    assert [row["circuit_id"] for row in items] == [mine["id"]]
    assert items[0]["sitting_name"] == "Finals"
    assert items[0]["slot_count"] == 1
    assert items[0]["in_progress"] is False

    # Somebody else in the same org, supervising nothing, gets an empty list
    # rather than everybody's circuits.
    assert (await client.get("/api/v1/orgs/kings/supervisor/circuits", headers=bearer(supervisor))).json()[
        "items"
    ] == []


async def _token_for(make_actor, org_id: uuid.UUID, user_id: uuid.UUID) -> str:  # type: ignore[no-untyped-def]
    """A token for a user who already exists, carrying their org membership."""
    from tests.support.tokens import mint_token

    return mint_token(
        user_id=user_id,
        email="sup@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="supervisor"),),
        active_org_slug="kings",
    )


async def test_a_started_circuit_reads_as_in_progress(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings")
    station = await published_station(client, admin, "kings", "S1")
    supervisor_id = await a_user(db_session, "sup@example.com")
    circuit = await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(await a_user(db_session, "cand@example.com"))],
        station_version_ids=[station],
        supervisor_user_id=str(supervisor_id),
    )
    await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/start", headers=bearer(admin))

    token = await _token_for(make_actor, org_id, supervisor_id)
    row = (await client.get("/api/v1/orgs/kings/supervisor/circuits", headers=bearer(token))).json()["items"][
        0
    ]
    assert row["in_progress"] is True
    assert row["ended"] is False


# --- the console -----------------------------------------------------------


async def test_the_console_names_every_candidate_and_station_once(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings")
    stations = [
        await published_station(client, admin, "kings", "Chest pain"),
        await published_station(client, admin, "kings", "Headache"),
    ]
    candidate = await a_user(db_session, "cand@example.com")
    await client.post(
        "/api/v1/orgs/kings/trainees",
        json={"email": "cand@example.com", "first_name": "Ada", "last_name": "Lovelace"},
        headers=bearer(admin),
    )
    supervisor_id = await a_user(db_session, "sup@example.com")
    circuit = await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(candidate)],
        station_version_ids=stations,
        supervisor_user_id=str(supervisor_id),
    )

    response = await client.get(f"/api/v1/orgs/kings/circuits/{circuit['id']}/console", headers=bearer(admin))
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["sitting"]["name"] == "Finals"
    assert body["sitting"]["mode"] == "exam"
    assert body["circuit"]["supervisor"]["email"] == "sup@example.com"
    assert body["circuit"]["agent_dispatched"] is False
    assert body["circuit"]["editable"] is True
    assert body["circuit"]["timing"]["simulation_minutes"] > 0

    assert [slot["station"]["title"] for slot in body["slots"]] == ["Chest pain", "Headache"]
    assert {slot["trainee"]["email"] for slot in body["slots"]} == {"cand@example.com"}
    # The roster entry is resolved from the slot's user id: two ids, one person.
    assert body["slots"][0]["trainee"]["trainee_id"] is not None
    assert all(slot["has_review"] is False for slot in body["slots"])
    assert all(slot["is_active"] is False for slot in body["slots"])


async def test_the_console_follows_the_live_circuit(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """The eight-second poll: which slot is live, and in which room."""
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings", mode="training")
    station = await published_station(client, admin, "kings", "S1")
    circuit = await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(await a_user(db_session, "cand@example.com"))],
        station_version_ids=[station],
    )
    await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/start", headers=bearer(admin))
    slot_id = circuit["slots"][0]["id"]
    await client.post(
        f"/api/v1/orgs/kings/circuits/{circuit['id']}/switch-turn",
        json={"slot_id": slot_id},
        headers=bearer(admin),
    )

    body = (
        await client.get(f"/api/v1/orgs/kings/circuits/{circuit['id']}/console", headers=bearer(admin))
    ).json()
    assert body["circuit"]["active_slot_id"] == slot_id
    assert body["circuit"]["room_name"] == f"circuit_{circuit['id']}"
    assert [slot["is_active"] for slot in body["slots"]] == [True]
    assert body["slots"][0]["room_name"] == body["circuit"]["room_name"]


async def test_the_console_refuses_another_organisations_circuit(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    other_id, other_admin = await org_with_admin(client, make_actor, slug="guys")
    sitting = await a_sitting(client, admin, "kings")
    station = await published_station(client, admin, "kings", "S1")
    circuit = await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(await a_user(db_session, "cand@example.com"))],
        station_version_ids=[station],
    )

    response = await client.get(
        f"/api/v1/orgs/guys/circuits/{circuit['id']}/console", headers=bearer(other_admin)
    )
    assert response.status_code == 404
    assert response.json()["code"] == "circuit_not_found"


# --- the trainee portal ----------------------------------------------------


async def test_a_trainee_sees_their_sittings_and_whether_to_join(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings")
    station = await published_station(client, admin, "kings", "Chest pain")
    candidate = await make_actor(
        "me@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="trainee"),),
        active_org_slug="kings",
    )
    candidate_id = await a_user(db_session, "me@example.com")
    circuit = await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(candidate_id)],
        station_version_ids=[station],
    )

    before = (await client.get("/api/v1/me/sittings", headers=bearer(candidate))).json()
    assert [item["circuit_id"] for item in before["items"]] == [circuit["id"]]
    assert before["items"][0]["org_slug"] == "kings"
    assert before["items"][0]["slots"][0]["station_title"] == "Chest pain"
    # Not started: there is no room to join, and the portal must not offer one.
    assert before["items"][0]["slots"][0]["joinable"] is False

    await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/start", headers=bearer(admin))
    after = (await client.get("/api/v1/me/sittings", headers=bearer(candidate))).json()
    assert after["items"][0]["slots"][0]["joinable"] is True
    assert after["items"][0]["slots"][0]["room_name"] == f"circuit_{circuit['id']}"


async def test_someone_rostered_nowhere_gets_an_empty_list(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("nobody@example.com")
    response = await client.get("/api/v1/me/sittings", headers=bearer(token))
    assert response.status_code == 200
    assert response.json()["items"] == []


async def test_my_sittings_needs_a_token(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/me/sittings")).status_code == 401
