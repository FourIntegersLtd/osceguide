"""The sitting report: one request for what a course lead reads back."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from tests.http.test_org_read_models import a_circuit
from tests.support.sittings import a_sitting, a_trainee, org_with_admin, published_station
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
        json={"field_values": {"consulting.score": "a"}, "status": "completed"},
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
    assert body["totals"] == {
        "candidates": 1,
        "stations": 2,
        "stations_marked": 1,
        "decisions_released": 0,
        "awaiting_marking": 0,
    }
    [row] = body["candidates"]
    assert row["email"] == "cand@example.com"
    assert row["trainee_id"] == trainee_id
    assert [s["station_title"] for s in row["stations"]] == ["Chest pain", "Headache"]
    assert row["stations"][0]["attempt_status"] == "created"
    assert row["stations"][0]["by_domain"] == {"consulting": "A"}
    assert row["stations"][1]["attempt_status"] is None
    assert row["overall_rag"] == "A"
    assert row["decision"]["workflow_state"] == "draft"
    assert row["decision"]["assessment_outcome"] == "pass"


async def test_a_candidate_no_longer_on_the_roster_and_undecided_still_appears(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """A slot names a `users.id`, so a candidate rostered when the circuit was
    built but whose roster entry is later removed still has a slot. The report
    must still show them — with no resolved `trainee_id` and no decision —
    rather than drop them. (Since SEC-014, a candidate must be on the roster to
    be enrolled in the first place; this is the entry going away afterwards.)"""
    from sqlalchemy import delete

    from app.features.roster.models import Trainee

    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings", mode="exam")
    station = await published_station(client, admin, "kings", "S1")
    candidate = await a_trainee(db_session, "leaver@example.com")
    await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(candidate)],
        station_version_ids=[station],
    )
    # The roster entry is removed after scheduling: the slot survives, the link
    # to a trainee does not.
    await db_session.execute(delete(Trainee).where(Trainee.user_id == candidate))
    await db_session.commit()

    body = (
        await client.get(f"/api/v1/orgs/kings/sittings/{sitting['id']}/report", headers=bearer(admin))
    ).json()
    [row] = body["candidates"]
    assert row["trainee_id"] is None
    assert row["decision"] is None
    assert row["overall_rag"] is None


async def test_the_report_is_for_staff_and_this_organisation_only(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """R-6: a supervisor opening Results read a 403 page. Staff read the report; a
    trainee member still cannot, and the CSV export stays an org admin's."""
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings", mode="exam")
    supervisor = await make_actor(
        "sup@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="supervisor"),),
        active_org_slug="kings",
    )
    trainee = await make_actor(
        "member-trainee@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="trainee"),),
        active_org_slug="kings",
    )
    report = f"/api/v1/orgs/kings/sittings/{sitting['id']}/report"
    read = await client.get(report, headers=bearer(supervisor))
    assert read.status_code == 200, read.text
    assert read.json()["sitting"]["name"] == sitting["name"]
    assert (await client.get(report, headers=bearer(trainee))).status_code == 403
    assert (await client.get(f"{report}.csv", headers=bearer(supervisor))).status_code == 403

    _, other = await org_with_admin(client, make_actor, slug="guys")
    elsewhere = await client.get(f"/api/v1/orgs/guys/sittings/{sitting['id']}/report", headers=bearer(other))
    assert elsewhere.status_code == 404
    assert elsewhere.json()["code"] == "sitting_not_found"


async def test_a_skipped_station_is_absent_until_a_human_review_marks_it(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """R-42: a skipped slot is an absent result, not an unmarked one; a completed review counts as marked."""
    from app.features.voice.service import get_room_agents
    from tests.support.fakes import FakeRoomAgents

    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings", mode="exam")
    station = await published_station(client, admin, "kings", "Chest pain")
    rostered = await client.post(
        "/api/v1/orgs/kings/trainees",
        json={"email": "cand@example.com", "first_name": "Ada", "last_name": "Lovelace"},
        headers=bearer(admin),
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
    ended = await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/end", headers=bearer(admin))
    assert ended.status_code == 200, ended.text
    slot_id = circuit["slots"][0]["id"]
    url = f"/api/v1/orgs/kings/sittings/{sitting['id']}/report"

    body = (await client.get(url, headers=bearer(admin))).json()
    [row] = body["candidates"]
    assert row["stations"][0]["slot_status"] == "skipped"
    assert row["stations"][0]["absent"] is True
    assert (body["totals"]["stations"], body["totals"]["stations_marked"]) == (0, 0)

    reviewed = await client.put(
        f"/api/v1/orgs/kings/slots/{slot_id}/reviews/mine",
        json={"field_values": {"consulting.score": "a"}, "status": "completed"},
        headers=bearer(admin),
    )
    assert reviewed.status_code == 200, reviewed.text

    body = (await client.get(url, headers=bearer(admin))).json()
    [row] = body["candidates"]
    assert (row["stations"][0]["marked"], row["stations"][0]["absent"]) == (True, False)
    assert (body["totals"]["stations"], body["totals"]["stations_marked"]) == (1, 1)
