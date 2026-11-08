"""A station on a circuit can name its own assessor (hire board: Who assesses?). Display only."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.http.test_examiner_transcript_routes import an_examiner
from tests.http.test_sittings_routes import a_template_version
from tests.support.sittings import a_trainee, org_with_admin, published_station
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def _setup(client: AsyncClient, db_session: AsyncSession, make_actor):  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    template = await a_template_version(client, admin)
    sitting = (
        await client.post(
            "/api/v1/orgs/kings/sittings",
            json={"name": "Finals", "programme_id": str(template), "mode": "exam"},
            headers=bearer(admin),
        )
    ).json()
    stations = [
        await published_station(client, admin, "kings", "Sore knee"),
        await published_station(client, admin, "kings", "Chest pain"),
    ]
    candidate = await a_trainee(db_session, "cand@example.com")
    assessor, _ = await an_examiner(db_session, org_id, "dan@example.com")
    return admin, sitting["id"], stations, candidate, assessor


def _assessors(circuit: dict) -> list[str | None]:  # type: ignore[type-arg]
    return [slot["assessor_user_id"] for slot in sorted(circuit["slots"], key=lambda s: s["slot_index"])]


async def test_a_station_names_its_assessor_and_an_edit_changes_or_clears_it(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    admin, sitting_id, stations, candidate, assessor = await _setup(client, db_session, make_actor)
    created = await client.post(
        f"/api/v1/orgs/kings/sittings/{sitting_id}/circuits",
        json={
            "name": "Room 1",
            "trainee_ids": [str(candidate)],
            "station_version_ids": stations,
            "station_assessor_ids": [str(assessor), None],
        },
        headers=bearer(admin),
    )
    assert created.status_code == 201, created.text
    assert _assessors(created.json()) == [str(assessor), None]
    sitting = await client.get(f"/api/v1/orgs/kings/sittings/{sitting_id}", headers=bearer(admin))
    assert sitting.json()["circuits"][0]["assessor_names"] == ["dan@example.com"]

    base = {"trainee_ids": [str(candidate)], "station_version_ids": stations, "timing": {}}
    kept = await client.put(
        f"/api/v1/orgs/kings/circuits/{created.json()['id']}", json=base, headers=bearer(admin)
    )
    assert _assessors(kept.json()) == [str(assessor), None]

    cleared = await client.put(
        f"/api/v1/orgs/kings/circuits/{created.json()['id']}",
        json={**base, "station_assessor_ids": [None, None]},
        headers=bearer(admin),
    )
    assert cleared.status_code == 200, cleared.text
    assert _assessors(cleared.json()) == [None, None]


async def test_bulk_exam_circuits_carry_the_assessors(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    admin, sitting_id, stations, candidate, assessor = await _setup(client, db_session, make_actor)
    created = await client.post(
        f"/api/v1/orgs/kings/sittings/{sitting_id}/circuits/bulk",
        json={
            "candidate_user_ids": [str(candidate)],
            "station_version_ids": stations,
            "station_assessor_ids": [None, str(assessor)],
        },
        headers=bearer(admin),
    )
    assert created.status_code == 201, created.text
    assert _assessors(created.json()[0]) == [None, str(assessor)]


async def test_the_same_station_twice_keeps_each_positions_assessor(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    admin, sitting_id, stations, candidate, assessor = await _setup(client, db_session, make_actor)
    twice = await client.post(
        f"/api/v1/orgs/kings/sittings/{sitting_id}/circuits",
        json={
            "name": "Room 1",
            "trainee_ids": [str(candidate)],
            "station_version_ids": [stations[0], stations[0]],
            "station_assessor_ids": [str(assessor), None],
        },
        headers=bearer(admin),
    )
    assert twice.status_code == 201, twice.text
    assert _assessors(twice.json()) == [str(assessor), None]
    kept = await client.put(
        f"/api/v1/orgs/kings/circuits/{twice.json()['id']}",
        json={"trainee_ids": [str(candidate)], "station_version_ids": [stations[0], stations[0]], "timing": {}},
        headers=bearer(admin),
    )
    assert _assessors(kept.json()) == [str(assessor), None]


async def test_the_assessor_list_must_pair_with_the_stations(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    admin, sitting_id, stations, candidate, assessor = await _setup(client, db_session, make_actor)
    body = {"name": "Room 1", "trainee_ids": [str(candidate)], "station_version_ids": stations}
    unpaired = await client.post(
        f"/api/v1/orgs/kings/sittings/{sitting_id}/circuits",
        json={**body, "station_assessor_ids": [str(assessor)]},
        headers=bearer(admin),
    )
    assert (unpaired.status_code, unpaired.json()["code"]) == (409, "invalid_circuit")


async def test_an_empty_assessor_list_is_not_a_clear_all(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    admin, sitting_id, stations, candidate, _ = await _setup(client, db_session, make_actor)
    empty = await client.post(
        f"/api/v1/orgs/kings/sittings/{sitting_id}/circuits",
        json={
            "name": "Room 1",
            "trainee_ids": [str(candidate)],
            "station_version_ids": stations,
            "station_assessor_ids": [],
        },
        headers=bearer(admin),
    )
    assert (empty.status_code, empty.json()["code"]) == (409, "invalid_circuit")


async def test_a_candidate_cannot_assess(client: AsyncClient, db_session: AsyncSession, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin, sitting_id, stations, candidate, assessor = await _setup(client, db_session, make_actor)
    url = f"/api/v1/orgs/kings/sittings/{sitting_id}/circuits"
    body = {"name": "Room 1", "trainee_ids": [str(candidate)], "station_version_ids": stations}
    refused = await client.post(
        url, json={**body, "station_assessor_ids": [str(candidate), None]}, headers=bearer(admin)
    )
    assert (refused.status_code, refused.json()["code"]) == (409, "lead_cannot_run")


async def test_the_console_shows_each_stations_assessor(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    admin, sitting_id, stations, candidate, assessor = await _setup(client, db_session, make_actor)
    created = await client.post(
        f"/api/v1/orgs/kings/sittings/{sitting_id}/circuits",
        json={
            "name": "Room 1",
            "trainee_ids": [str(candidate)],
            "station_version_ids": stations,
            "station_assessor_ids": [str(assessor), None],
        },
        headers=bearer(admin),
    )
    console = await client.get(
        f"/api/v1/orgs/kings/circuits/{created.json()['id']}/console", headers=bearer(admin)
    )
    assert console.status_code == 200, console.text
    slots = sorted(console.json()["slots"], key=lambda slot: slot["slot_index"])
    assert [(slot["assessor"] or {}).get("user_id") for slot in slots] == [str(assessor), None]
