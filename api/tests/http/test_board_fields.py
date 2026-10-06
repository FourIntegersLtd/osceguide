"""The counts and names the institution boards show beside each row."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.http.test_org_read_models import a_circuit, a_user
from tests.http.test_sittings_routes import org_with_admin, published_station
from tests.support.sittings import add_programme, create_sitting_body
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def _sitting(client: AsyncClient, admin: str, programme_id: uuid.UUID, name: str) -> dict:
    created = await client.post(
        "/api/v1/orgs/kings/sittings",
        json=create_sitting_body(name=name, programme_id=programme_id, mode="training"),
        headers=bearer(admin),
    )
    assert created.status_code == 201, created.text
    return created.json()


async def test_sittings_carry_their_programme_name_and_candidate_count(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    programme_id = await add_programme(client, admin, org_slug="kings")
    exam_name = "SCA"
    sitting = await _sitting(client, admin, programme_id, "Mock A")
    empty = await _sitting(client, admin, programme_id, "Mock B")
    stations = [
        await published_station(client, admin, "kings", "Chest pain"),
        await published_station(client, admin, "kings", "Headache"),
    ]
    ada = await a_user(db_session, "ada@example.com")
    bob = await a_user(db_session, "bob@example.com")
    for name, people in (("One", [ada, bob]), ("Two", [ada])):
        body = {
            "name": name,
            "trainee_ids": [str(p) for p in people],
            "station_version_ids": stations[: len(people)],
        }
        made = await client.post(
            f"/api/v1/orgs/kings/sittings/{sitting['id']}/circuits", json=body, headers=bearer(admin)
        )
        assert made.status_code == 201, made.text

    listed = (await client.get("/api/v1/orgs/kings/sittings", headers=bearer(admin))).json()["items"]
    by_name = {item["name"]: item for item in listed}
    # Ada is on both circuits and counts once.
    assert by_name["Mock A"]["candidate_count"] == 2
    assert by_name["Mock A"]["programme_name"] == exam_name
    assert by_name["Mock B"]["candidate_count"] == 0
    assert by_name["Mock B"]["programme_name"] == exam_name
    assert empty["id"] in {item["id"] for item in listed}

    detail = (await client.get(f"/api/v1/orgs/kings/sittings/{sitting['id']}", headers=bearer(admin))).json()
    assert detail["candidate_count"] == 2
    assert detail["programme_name"] == exam_name
    # The sitting's exam code is what the circuit builder filters the station library by.
    assert detail["exam_code"] == "sca"
    assert {item["exam_code"] for item in listed} == {"sca"}


async def test_circuits_carry_trainee_count_and_supervisor_name(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    programme_id = await add_programme(client, admin, org_slug="kings")
    sitting = await _sitting(client, admin, programme_id, "Mock A")
    stations = [
        await published_station(client, admin, "kings", "Chest pain"),
        await published_station(client, admin, "kings", "Headache"),
    ]
    ada = await a_user(db_session, "ada@example.com")
    bob = await a_user(db_session, "bob@example.com")
    lead = await a_user(db_session, "lead@example.com")
    await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(ada), str(bob)],
        station_version_ids=stations,
        supervisor_user_id=str(lead),
    )
    await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(ada)],
        station_version_ids=stations[:1],
    )

    detail = (await client.get(f"/api/v1/orgs/kings/sittings/{sitting['id']}", headers=bearer(admin))).json()
    first, second = detail["circuits"]
    assert (first["trainee_count"], first["supervisor_name"]) == (2, "lead@example.com")
    assert (second["trainee_count"], second["supervisor_name"]) == (1, None)


async def test_trainees_carry_programmes_and_stations_sat(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from sqlalchemy import update

    from app.features.sittings.models import Slot

    _, admin = await org_with_admin(client, make_actor)
    programme_id = await add_programme(client, admin, org_slug="kings")
    exam_name = "SCA"
    sitting = await _sitting(client, admin, programme_id, "Mock A")
    stations = [
        await published_station(client, admin, "kings", "Chest pain"),
        await published_station(client, admin, "kings", "Headache"),
    ]
    ada = await a_user(db_session, "ada@example.com")
    await a_user(db_session, "idle@example.com")
    await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(ada)],
        station_version_ids=stations[:1],
    )
    await db_session.execute(
        update(Slot).where(Slot.trainee_id == ada, Slot.slot_index == 0).values(status="completed")
    )

    listed = (await client.get("/api/v1/orgs/kings/trainees", headers=bearer(admin))).json()["items"]
    by_email = {item["email"]: item for item in listed}
    assert by_email["ada@example.com"]["programme_names"] == [exam_name]
    assert by_email["ada@example.com"]["stations_sat"] == 1
    assert by_email["idle@example.com"]["programme_names"] == []
    assert by_email["idle@example.com"]["stations_sat"] == 0


async def test_members_carry_the_number_of_circuits_they_lead(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    programme_id = await add_programme(client, admin, org_slug="kings")
    sitting = await _sitting(client, admin, programme_id, "Mock A")
    station = await published_station(client, admin, "kings", "Chest pain")
    ada = await a_user(db_session, "ada@example.com")
    lead = await a_user(db_session, "lead@example.com")
    await client.post(
        "/api/v1/orgs/kings/memberships",
        json={"email": "lead@example.com", "role": "supervisor"},
        headers=bearer(admin),
    )
    for _ in range(2):
        await a_circuit(
            client,
            admin,
            "kings",
            sitting_id=sitting["id"],
            trainee_ids=[str(ada)],
            station_version_ids=[station],
            supervisor_user_id=str(lead),
        )

    listed = (await client.get("/api/v1/orgs/kings/memberships", headers=bearer(admin))).json()["items"]
    by_email = {item["email"]: item["circuits_led"] for item in listed}
    assert by_email["lead@example.com"] == 2
    assert by_email["admin-kings@example.com"] == 0


async def test_the_report_counts_candidates_still_awaiting_marking(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from sqlalchemy import update

    from app.features.sittings.models import Slot

    _, admin = await org_with_admin(client, make_actor)
    programme_id = await add_programme(client, admin, org_slug="kings")
    sitting = await _sitting(client, admin, programme_id, "Mock A")
    stations = [
        await published_station(client, admin, "kings", "Chest pain"),
        await published_station(client, admin, "kings", "Headache"),
    ]
    ada = await a_user(db_session, "ada@example.com")
    bob = await a_user(db_session, "bob@example.com")
    await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(ada), str(bob)],
        station_version_ids=stations,
    )
    # Ada has sat her station and nothing has marked it; Bob has not sat his.
    await db_session.execute(update(Slot).where(Slot.trainee_id == ada).values(status="completed"))

    report = await client.get(f"/api/v1/orgs/kings/sittings/{sitting['id']}/report", headers=bearer(admin))
    assert report.status_code == 200, report.text
    assert report.json()["totals"]["awaiting_marking"] == 1
    assert report.json()["totals"]["candidates"] == 2
