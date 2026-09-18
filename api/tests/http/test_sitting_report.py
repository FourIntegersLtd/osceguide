"""The sitting report: one request for what a course lead reads back."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from tests.http.test_org_read_models import a_circuit, a_sitting, a_user
from tests.http.test_sittings_routes import org_with_admin, published_station
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def test_the_report_lists_every_candidate_with_marking_ratings_and_decision(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from app.features.voice.service import get_room_agents
    from tests.support.fakes import FakeRoomAgents

    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings", mode="exam")
    stations = [
        await published_station(client, admin, "kings", "Chest pain"),
        await published_station(client, admin, "kings", "Headache"),
    ]
    rostered = await client.post(
        "/api/v1/orgs/kings/trainees",
        json={"email": "cand@example.com", "first_name": "Ada", "last_name": "Lovelace"},
        headers=bearer(admin),
    )
    trainee_id = rostered.json()["id"]
    candidate = uuid.UUID(rostered.json()["user_id"])
    circuit = await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(candidate)],
        station_version_ids=stations,
    )
    client._transport.app.dependency_overrides[get_room_agents] = lambda: FakeRoomAgents()  # type: ignore[attr-defined]
    await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/start", headers=bearer(admin))
    first_slot = circuit["slots"][0]["id"]
    # Advancing out of the reading period is what puts the patient in, and the
    # recording is created as it happens.
    await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/advance", json={}, headers=bearer(admin))
    reviewed = await client.put(
        f"/api/v1/orgs/kings/slots/{first_slot}/reviews/mine",
        json={"field_values": {"communication.score": "a"}, "status": "completed"},
        headers=bearer(admin),
    )
    assert reviewed.status_code == 200, reviewed.text
    decided = await client.put(
        f"/api/v1/orgs/kings/sittings/{sitting['id']}/candidates/{trainee_id}/decision",
        json={"assessment_outcome": "pass", "rationale": "Safe and thorough"},
        headers=bearer(admin),
    )
    assert decided.status_code == 200, decided.text

    report = await client.get(f"/api/v1/orgs/kings/sittings/{sitting['id']}/report", headers=bearer(admin))
    assert report.status_code == 200, report.text
    body = report.json()

    assert body["sitting"]["name"] == "Finals"
    assert body["totals"] == {"candidates": 1, "stations": 2, "stations_marked": 0, "decisions_released": 0}
    [row] = body["candidates"]
    assert row["email"] == "cand@example.com"
    assert row["trainee_id"] == trainee_id
    assert [s["station_title"] for s in row["stations"]] == ["Chest pain", "Headache"]
    assert row["stations"][0]["attempt_status"] == "created"
    assert row["stations"][0]["by_domain"] == {"communication": "A"}
    assert row["stations"][1]["attempt_status"] is None
    assert row["overall_rag"] == "A"
    assert row["decision"]["workflow_state"] == "draft"
    assert row["decision"]["assessment_outcome"] == "pass"


async def test_a_candidate_off_the_roster_and_undecided_still_appears(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings", mode="exam")
    station = await published_station(client, admin, "kings", "S1")
    stranger = await a_user(db_session, "unrostered@example.com")
    await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(stranger)],
        station_version_ids=[station],
    )

    body = (
        await client.get(f"/api/v1/orgs/kings/sittings/{sitting['id']}/report", headers=bearer(admin))
    ).json()
    [row] = body["candidates"]
    assert row["trainee_id"] is None
    assert row["decision"] is None
    assert row["overall_rag"] is None


async def test_the_report_is_for_admins_and_this_organisation_only(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings", mode="exam")
    supervisor = await make_actor(
        "sup@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="supervisor"),),
        active_org_slug="kings",
    )
    assert (
        await client.get(f"/api/v1/orgs/kings/sittings/{sitting['id']}/report", headers=bearer(supervisor))
    ).status_code == 403

    _, other = await org_with_admin(client, make_actor, slug="guys")
    elsewhere = await client.get(f"/api/v1/orgs/guys/sittings/{sitting['id']}/report", headers=bearer(other))
    assert elsewhere.status_code == 404
    assert elsewhere.json()["code"] == "sitting_not_found"
