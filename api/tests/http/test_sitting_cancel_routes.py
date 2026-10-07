"""R-7: a sitting can be called off and a circuit removed, and neither grows once results are settled.

One refusal per test at most, and last: a refused request rolls back the
shared test session, and the fixtures with it.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.http.test_org_read_models import a_circuit, a_sitting
from tests.http.test_results_routes import EVIDENCE, a_sitting_and_trainee, url
from tests.http.test_sittings_routes import org_with_admin, published_station
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def _rostered(client: AsyncClient, admin: str, email: str) -> str:
    """A roster entry's account id, which is what a circuit is built from."""
    rostered = await client.post(
        "/api/v1/orgs/kings/trainees", json={"email": email, "first_name": "Ada"}, headers=bearer(admin)
    )
    assert rostered.status_code == 201, rostered.text
    return str(rostered.json()["user_id"])


async def test_a_cancelled_sitting_is_kept_and_takes_no_new_circuit(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings")
    station = await published_station(client, admin, "kings", "Chest pain")
    trainee = await _rostered(client, admin, "cancel-one@example.com")

    cancelled = await client.post(
        f"/api/v1/orgs/kings/sittings/{sitting['id']}/cancel", headers=bearer(admin)
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "cancelled"
    again = await client.post(f"/api/v1/orgs/kings/sittings/{sitting['id']}/cancel", headers=bearer(admin))
    assert (again.status_code, again.json()["status"]) == (200, "cancelled")

    refused = await client.post(
        f"/api/v1/orgs/kings/sittings/{sitting['id']}/circuits",
        json={"name": "Late", "trainee_ids": [trainee], "station_version_ids": [station]},
        headers=bearer(admin),
    )
    assert (refused.status_code, refused.json()["code"]) == (409, "sitting_locked")


async def test_a_sitting_that_has_begun_cannot_be_cancelled(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings")
    station = await published_station(client, admin, "kings", "Chest pain")
    circuit = await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[await _rostered(client, admin, "cancel-two@example.com")],
        station_version_ids=[station],
    )
    started = await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/start", headers=bearer(admin))
    assert started.status_code == 200, started.text

    refused = await client.post(f"/api/v1/orgs/kings/sittings/{sitting['id']}/cancel", headers=bearer(admin))

    assert (refused.status_code, refused.json()["code"]) == (409, "sitting_locked")


async def test_a_circuit_nobody_ran_can_be_removed_and_a_started_one_cannot(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    _org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings")
    station = await published_station(client, admin, "kings", "Chest pain")
    trainee = await _rostered(client, admin, "cancel-three@example.com")
    spare = await a_circuit(
        client, admin, "kings", sitting_id=sitting["id"], trainee_ids=[trainee], station_version_ids=[station]
    )
    kept = await a_circuit(
        client, admin, "kings", sitting_id=sitting["id"], trainee_ids=[trainee], station_version_ids=[station]
    )

    removed = await client.delete(f"/api/v1/orgs/kings/circuits/{spare['id']}", headers=bearer(admin))
    assert removed.status_code == 204, removed.text
    read = await client.get(f"/api/v1/orgs/kings/sittings/{sitting['id']}", headers=bearer(admin))
    assert [circuit["id"] for circuit in read.json()["circuits"]] == [kept["id"]]

    await client.post(f"/api/v1/orgs/kings/circuits/{kept['id']}/start", headers=bearer(admin))
    refused = await client.delete(f"/api/v1/orgs/kings/circuits/{kept['id']}", headers=bearer(admin))
    assert (refused.status_code, refused.json()["code"]) == (409, "circuit_locked")


async def test_nobody_new_is_examined_once_a_result_is_signed_off(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting, candidate = await a_sitting_and_trainee(db_session, org_id)
    saved = await client.put(
        url(sitting, candidate),
        json={"assessment_outcome": "pass", "rationale": "Met the standard.", "evidence": EVIDENCE},
        headers=bearer(admin),
    )
    assert saved.status_code == 200, saved.text
    signed = await client.post(url(sitting, candidate, "/sign-off"), headers=bearer(admin))
    assert signed.status_code == 200, signed.text
    station = await published_station(client, admin, "kings", "Chest pain")

    refused = await client.post(
        f"/api/v1/orgs/kings/sittings/{sitting}/circuits",
        json={
            "name": "Latecomer",
            "trainee_ids": [await _rostered(client, admin, "late@example.com")],
            "station_version_ids": [station],
        },
        headers=bearer(admin),
    )

    assert (refused.status_code, refused.json()["code"]) == (409, "sitting_locked")
