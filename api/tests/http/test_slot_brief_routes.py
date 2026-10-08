"""A candidate's reading brief, during reading time (B50).

The circuit's attempt is created when the patient is dispatched, after reading, so the
brief is read by slot. A circuit built from a platform library station showed nothing:
the old pre-dispatch path only looked in the org's own station list.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.http.test_sittings_routes import a_template_version, a_trainee, published_station
from tests.support.sittings import org_with_admin
from tests.support.tokens import bearer, mint_token

pytestmark = pytest.mark.db

BRIEF = "Mrs Patel, 64, asks about her new tablets."


async def library_station(client: AsyncClient, make_actor) -> str:  # type: ignore[no-untyped-def]
    root = await make_actor(f"library-{uuid.uuid4().hex[:8]}@osceguide.com", platform_admin=True)
    created = await client.post(
        "/api/v1/platform/stations",
        json={
            "title": "Library S1",
            "exam_code": "sca",
            "content": {"reading_brief": BRIEF, "patient_information": {"persona": "x"}},
        },
        headers=bearer(root),
    )
    assert created.status_code == 201, created.text
    published = await client.post(
        f"/api/v1/platform/stations/{created.json()['id']}/versions/1/publish", headers=bearer(root)
    )
    assert published.status_code == 200, published.text
    return str(published.json()["id"])


async def a_circuit(client: AsyncClient, make_actor, db_session: AsyncSession, *, library: bool):  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    programme = await a_template_version(client, admin)
    sitting = (
        await client.post(
            "/api/v1/orgs/kings/sittings",
            json={"name": "S", "programme_id": str(programme), "mode": "exam"},
            headers=bearer(admin),
        )
    ).json()
    version = (
        await library_station(client, make_actor)
        if library
        else await published_station(client, admin, "kings", "Own S1")
    )
    trainee_id = await a_trainee(db_session, f"cand-{uuid.uuid4().hex[:8]}@example.com")
    circuit = (
        await client.post(
            f"/api/v1/orgs/kings/sittings/{sitting['id']}/circuits",
            json={"name": "C", "trainee_ids": [str(trainee_id)], "station_version_ids": [version]},
            headers=bearer(admin),
        )
    ).json()
    candidate = mint_token(user_id=trainee_id, email=f"c-{trainee_id}@example.com")
    slot_id = circuit["slots"][0]["id"]
    return admin, candidate, circuit["id"], slot_id


async def test_a_library_station_brief_is_readable_during_reading(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    admin, candidate, circuit_id, slot_id = await a_circuit(client, make_actor, db_session, library=True)

    before = await client.get(f"/api/v1/me/slots/{slot_id}/brief", headers=bearer(candidate))
    assert before.status_code == 409
    assert before.json()["code"] == "circuit_not_started"

    started = await client.post(f"/api/v1/orgs/kings/circuits/{circuit_id}/start", headers=bearer(admin))
    assert started.status_code == 200, started.text
    read = await client.get(f"/api/v1/me/slots/{slot_id}/brief", headers=bearer(candidate))
    assert read.status_code == 200, read.text
    assert read.json() == {"slot_id": slot_id, "station_title": "Library S1", "sections": [], "text": BRIEF}


async def test_an_org_station_brief_reads_the_same_way_and_never_for_a_stranger(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    admin, candidate, circuit_id, slot_id = await a_circuit(client, make_actor, db_session, library=False)
    await client.post(f"/api/v1/orgs/kings/circuits/{circuit_id}/start", headers=bearer(admin))

    read = await client.get(f"/api/v1/me/slots/{slot_id}/brief", headers=bearer(candidate))
    assert read.status_code == 200, read.text
    assert read.json()["station_title"] == "Own S1"
    stranger = await make_actor("stranger@example.com")
    assert (
        await client.get(f"/api/v1/me/slots/{slot_id}/brief", headers=bearer(stranger))
    ).status_code == 404


async def test_my_slot_review_before_release_is_null_and_a_strangers_is_not_found(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    """B51: an unreleased review is an ordinary state (200, not_released); someone else's slot is a 404."""
    _admin, candidate, _circuit_id, slot_id = await a_circuit(client, make_actor, db_session, library=False)
    mine = await client.get(f"/api/v1/me/slots/{slot_id}/review", headers=bearer(candidate))
    assert mine.status_code == 200, mine.text
    assert mine.json() == {"slot_id": str(slot_id), "state": "not_released"}
    stranger = await make_actor("review-stranger@example.com")
    theirs = await client.get(f"/api/v1/me/slots/{slot_id}/review", headers=bearer(stranger))
    assert theirs.status_code == 404
    assert theirs.json()["code"] == "slot_not_found"
