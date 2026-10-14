"""A free-trial learner's practice sets: capped at the stations they have left, titles withheld.

The trial covers a fixed number of stations. Without a cap at build time a free learner could make
a five-station session and only be refused at the fourth station, a dead end the setup screen
walked them into. And a station's title says what the case is, so a learner reads it only once
they have sat the station.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.http.test_station_sets_routes import a_learner, start
from tests.support.library import publish_library_station
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def stations(db_session: AsyncSession, count: int) -> list[uuid.UUID]:
    """`count` published SCA library stations, titled "Case 1", "Case 2" and so on."""
    return [
        await publish_library_station(db_session, title=f"Case {number}") for number in range(1, count + 1)
    ]


def body(version_ids: list[uuid.UUID], name: str = "Session 1") -> dict:
    return {"name": name, "exam_code": "sca", "station_version_ids": [str(v) for v in version_ids]}


async def sit_first_entry(client: AsyncClient, token: str, created: dict) -> None:
    entry_id = created["entries"][0]["id"]
    opened = await client.post(
        f"/api/v1/me/station-sets/{created['id']}/entries/{entry_id}/attempts", headers=bearer(token)
    )
    assert opened.status_code == 201, opened.text
    await start(client, opened.json()["attempt_id"])


async def test_a_trial_learner_cannot_build_a_session_bigger_than_their_free_stations(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("trial-cap@example.com")
    versions = await stations(db_session, 4)

    allowance = await client.get("/api/v1/me/station-sets/allowance?exam_code=sca", headers=bearer(token))
    assert allowance.status_code == 200, allowance.text
    assert allowance.json() == {"free_stations_left": 3}

    built = await client.post("/api/v1/me/station-sets", json=body(versions[:3]), headers=bearer(token))
    assert built.status_code == 201, built.text

    refused = await client.post("/api/v1/me/station-sets", json=body(versions), headers=bearer(token))
    assert refused.status_code == 403
    assert refused.json()["code"] == "trial_station_limit"
    assert refused.json()["details"] == {"stations_left": 3}


async def test_a_trial_learner_cannot_edit_a_session_past_their_free_stations(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """A station already sat costs nothing more; each new one costs one of what is left."""
    # Only staff edit a set; staff with no grant of their own are on the trial too.
    token = await make_actor("trial-edit@example.com", platform_admin=True)
    versions = await stations(db_session, 4)
    created = (
        await client.post("/api/v1/me/station-sets", json=body(versions[:3]), headers=bearer(token))
    ).json()
    await sit_first_entry(client, token, created)

    allowance = await client.get("/api/v1/me/station-sets/allowance?exam_code=sca", headers=bearer(token))
    assert allowance.json() == {"free_stations_left": 2}

    kept = await client.patch(
        f"/api/v1/me/station-sets/{created['id']}", json=body(versions[:3]), headers=bearer(token)
    )
    assert kept.status_code == 200, kept.text

    refused = await client.patch(
        f"/api/v1/me/station-sets/{created['id']}", json=body(versions), headers=bearer(token)
    )
    assert refused.status_code == 403
    assert refused.json()["code"] == "trial_station_limit"
    assert refused.json()["details"] == {"stations_left": 2}


async def test_a_paid_learner_has_no_cap(client: AsyncClient, db_session: AsyncSession, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await a_learner(client, db_session, make_actor, "paid-cap@example.com")
    versions = await stations(db_session, 5)

    allowance = await client.get("/api/v1/me/station-sets/allowance?exam_code=sca", headers=bearer(token))
    assert allowance.json() == {"free_stations_left": None}

    built = await client.post("/api/v1/me/station-sets", json=body(versions), headers=bearer(token))
    assert built.status_code == 201, built.text
    assert built.json()["total_entries"] == 5


async def test_a_station_title_is_withheld_until_it_has_been_sat(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    token = await a_learner(client, db_session, make_actor, "titles@example.com")
    versions = await stations(db_session, 2)
    created = (
        await client.post("/api/v1/me/station-sets", json=body(versions), headers=bearer(token))
    ).json()
    assert [entry["station_title"] for entry in created["entries"]] == [None, None]

    await sit_first_entry(client, token, created)

    read = await client.get(f"/api/v1/me/station-sets/{created['id']}", headers=bearer(token))
    assert [entry["station_title"] for entry in read.json()["entries"]] == ["Case 1", None]
    listed = await client.get("/api/v1/me/station-sets", headers=bearer(token))
    assert [entry["station_title"] for entry in listed.json()["items"][0]["entries"]] == ["Case 1", None]
