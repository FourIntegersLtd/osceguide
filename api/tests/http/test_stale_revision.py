"""B-15: two admins editing at once. A write that names an old revision is refused.

Every editable record carries a `revision` that each edit raises by one. A client that
sends the revision it read has its write refused with 409 `stale_revision` if someone
else has saved since; a client that sends none is unchanged.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.voice.service import get_room_agents
from tests.http.test_roster_edit_routes import add_trainee
from tests.http.test_sitting_edit_routes import a_circuit, a_sitting
from tests.http.test_sittings_routes import a_trainee, published_station
from tests.support.fakes import FakeRoomAgents
from tests.support.rubrics import MINIMAL_RUBRIC, PACING, SYSTEM_PROMPT, create_rubric
from tests.support.sittings import org_with_admin
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


@pytest.fixture
def agents(client: AsyncClient) -> FakeRoomAgents:
    """A patient that never reaches LiveKit: starting a circuit touches the room."""
    fake = FakeRoomAgents()
    client._transport.app.dependency_overrides[get_room_agents] = lambda: fake  # type: ignore[attr-defined]
    return fake


async def two_writes(
    client: AsyncClient,
    method: str,
    url: str,
    admin: str,
    body: dict,
    read: dict,
    *,
    other: dict | None = None,
) -> None:  # type: ignore[type-arg]
    """Save at the revision read, then again at the same revision: only the first lands."""
    assert read["revision"] == 1
    first = await client.request(method, url, json={**body, "revision": 1}, headers=bearer(admin))
    unchecked = await client.request(method, url, json=other or body, headers=bearer(admin))
    # Last: a refused request rolls back the test's shared session (api/AGENTS.md).
    stale = await client.request(method, url, json={**body, "revision": 1}, headers=bearer(admin))
    assert first.status_code == 200, first.text
    assert first.json()["revision"] == 2
    assert unchecked.status_code == 200, unchecked.text
    assert unchecked.json()["revision"] == 3
    assert stale.status_code == 409, stale.text
    assert stale.json()["code"] == "stale_revision"


async def test_a_roster_entry_edit_at_an_old_revision_is_refused(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    trainee_id = await add_trainee(client, admin, "a@example.com")
    read = (await client.get("/api/v1/orgs/kings/trainees", headers=bearer(admin))).json()["items"][0]

    await two_writes(
        client, "PATCH", f"/api/v1/orgs/kings/trainees/{trainee_id}", admin, {"first_name": "Amy"}, read
    )


async def test_a_sitting_edit_at_an_old_revision_is_refused(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin)

    await two_writes(
        client,
        "PUT",
        f"/api/v1/orgs/kings/sittings/{sitting['id']}",
        admin,
        {"name": "Renamed"},
        sitting,
        other={"name": "Again"},
    )


async def test_a_circuit_rebuild_at_an_old_revision_is_refused(
    client: AsyncClient, make_actor, db_session: AsyncSession, agents
) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin)
    trainee = str(await a_trainee(db_session, f"c-{uuid.uuid4().hex[:6]}@example.com"))
    station = await published_station(client, admin, "kings", "Abdo pain")
    circuit = await a_circuit(client, db_session, admin, sitting["id"])
    body = {"trainee_ids": [trainee], "station_version_ids": [station]}

    await two_writes(client, "PUT", f"/api/v1/orgs/kings/circuits/{circuit['id']}", admin, body, circuit)


async def test_a_rubric_draft_edit_at_an_old_revision_is_refused(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    rubric = await create_rubric(client, admin, org_slug="kings", title="Ours", publish=False)
    body = {"structure": MINIMAL_RUBRIC, "system_prompt": SYSTEM_PROMPT, "pacing": PACING}

    await two_writes(
        client,
        "PATCH",
        f"/api/v1/orgs/kings/rubrics/{rubric['id']}/versions/1",
        admin,
        body,
        rubric["versions"][0],
    )


async def test_an_exam_edit_at_an_old_revision_is_refused(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    rubric = await create_rubric(client, admin, org_slug="kings", title="Ours")
    created = await client.post(
        "/api/v1/orgs/kings/exams",
        json={
            "code": "own",
            "name": "Own",
            "default_reading_seconds": 60,
            "default_simulation_seconds": 300,
            "rubric_version_id": rubric["version_id"],
        },
        headers=bearer(admin),
    )
    assert created.status_code == 201, created.text

    await two_writes(
        client,
        "PATCH",
        f"/api/v1/orgs/kings/exams/{created.json()['id']}",
        admin,
        {"name": "Renamed"},
        created.json(),
    )
