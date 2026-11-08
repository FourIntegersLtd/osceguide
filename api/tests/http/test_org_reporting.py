"""R-32: an institution sees its sittings across a programme, not one report at a time."""

from __future__ import annotations

from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.http.test_org_read_models import a_circuit, a_user
from tests.support.decisions import seat_candidate, settle_decision
from tests.support.sittings import a_sitting, org_with_admin, published_station
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def test_reporting_sums_each_programmes_sittings_candidates_and_released_passes(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    first, second = await a_user(db_session, "one@example.com"), await a_user(db_session, "two@example.com")
    sitting = await a_sitting(client, admin, "kings")
    station = await published_station(client, admin, "kings", "Chest pain")
    for candidate in (first, second):
        await a_circuit(
            client,
            admin,
            "kings",
            sitting_id=sitting["id"],
            trainee_ids=[str(candidate)],
            station_version_ids=[station],
        )
    trainees = (await client.get("/api/v1/orgs/kings/trainees", headers=bearer(admin))).json()["items"]
    by_email = {t["email"]: t["id"] for t in trainees}
    await seat_candidate(db_session, org_id, UUID(sitting["id"]), UUID(by_email["one@example.com"]))
    await seat_candidate(db_session, org_id, UUID(sitting["id"]), UUID(by_email["two@example.com"]))
    for email, release in (("one@example.com", True), ("two@example.com", False)):
        trainee_id = by_email[email]
        await settle_decision(
            client, admin, org_slug="kings", sitting_id=sitting["id"], trainee_id=trainee_id, release=release
        )

    response = await client.get("/api/v1/orgs/kings/reporting", headers=bearer(admin))

    assert response.status_code == 200, response.text
    [row] = response.json()["programmes"]
    assert (row["sittings"], row["candidates"], row["released"], row["passed"]) == (1, 2, 1, 1)
    assert row["pass_rate"] == 100.0


async def test_reporting_is_closed_to_a_trainee(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    await org_with_admin(client, make_actor)
    stranger = await make_actor("learner@example.com")
    assert (await client.get("/api/v1/orgs/kings/reporting", headers=bearer(stranger))).status_code == 403


async def test_reporting_breaks_released_results_down_by_station_and_counts_assessors(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from app.features.voice.service import get_room_agents
    from tests.support.fakes import FakeRoomAgents

    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings")
    station = await published_station(client, admin, "kings", "Chest pain")
    rostered = await client.post(
        "/api/v1/orgs/kings/trainees", json={"email": "cand@example.com"}, headers=bearer(admin)
    )
    circuit = await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[rostered.json()["user_id"]],
        station_version_ids=[station],
    )
    client._transport.app.dependency_overrides[get_room_agents] = lambda: FakeRoomAgents()  # type: ignore[attr-defined]
    await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/start", headers=bearer(admin))
    await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/advance", json={}, headers=bearer(admin))
    reviewed = await client.put(
        f"/api/v1/orgs/kings/slots/{circuit['slots'][0]['id']}/reviews/mine",
        json={"field_values": {"consulting.score": "a"}, "status": "completed"},
        headers=bearer(admin),
    )
    assert reviewed.status_code == 200, reviewed.text
    await settle_decision(
        client,
        admin,
        org_slug="kings",
        sitting_id=sitting["id"],
        trainee_id=rostered.json()["id"],
        release=True,
    )

    body = (await client.get("/api/v1/orgs/kings/reporting", headers=bearer(admin))).json()

    assert body["assessors_marking"] == 1
    assert body["stations"] == [
        {"station_title": "Chest pain", "assessed": 1, "pass_rate": None, "weakest_competency": "Consulting"}
    ]


async def test_reporting_has_no_stations_before_anything_is_released(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)

    body = (await client.get("/api/v1/orgs/kings/reporting", headers=bearer(admin))).json()

    assert (body["stations"], body["assessors_marking"]) == ([], 0)
