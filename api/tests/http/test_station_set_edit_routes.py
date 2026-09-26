"""Renaming a practice set, and throwing one away.

`/me/station-sets` was a GET and a POST, so a learner could build a session and
never take it back apart — while the retiring client's own list offered a
rename and a delete on every row. Both writes are owner-only, and the shape of
the refusal is the point: a stranger is told `set_not_found` rather than
`forbidden`, because a set id is somebody's private list and an answer that
distinguishes "not yours" from "does not exist" confirms which ids are real.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.http.test_station_sets_routes import a_learner, a_station_version
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def a_set(client: AsyncClient, token: str, version: uuid.UUID, name: str = "Week one") -> dict:
    created = await client.post(
        "/api/v1/me/station-sets",
        json={"name": name, "exam_code": "sca", "station_version_ids": [str(version)]},
        headers=bearer(token),
    )
    assert created.status_code == 201, created.text
    return created.json()


# --- renaming ---------------------------------------------------------------


async def test_a_learner_renames_their_own_set(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """The name, and only the name.

    What the old edit screen offered besides the stations, and all there is to
    change: a set carries no description, and how long it takes is the exam's
    timings summed over its stations.
    """
    token = await a_learner(client, db_session, make_actor, "set-rename@example.com")
    version = await a_station_version(db_session)
    set_id = (await a_set(client, token, version))["id"]

    renamed = await client.patch(
        f"/api/v1/me/station-sets/{set_id}",
        json={"name": "Emergency cases"},
        headers=bearer(token),
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["name"] == "Emergency cases"
    # A rename is not a rebuild: the entries and their positions stand.
    assert [e["station_version_id"] for e in renamed.json()["entries"]] == [str(version)]
    assert renamed.json()["total_entries"] == 1

    read_back = await client.get(f"/api/v1/me/station-sets/{set_id}", headers=bearer(token))
    assert read_back.json()["name"] == "Emergency cases"


async def test_renaming_someone_elses_set_is_a_404_and_changes_nothing(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    owner = await a_learner(client, db_session, make_actor, "set-owner@example.com")
    stranger = await a_learner(client, db_session, make_actor, "set-stranger@example.com")
    version = await a_station_version(db_session)
    set_id = (await a_set(client, owner, version, name="Mine"))["id"]

    response = await client.patch(
        f"/api/v1/me/station-sets/{set_id}", json={"name": "Yours now"}, headers=bearer(stranger)
    )
    assert response.status_code == 404
    assert response.json()["code"] == "set_not_found"

    kept = await client.get(f"/api/v1/me/station-sets/{set_id}", headers=bearer(owner))
    assert kept.json()["name"] == "Mine"


async def test_a_set_keeps_a_name(client: AsyncClient, db_session: AsyncSession, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Blank is not a rename. The create route has always said so."""
    token = await a_learner(client, db_session, make_actor, "set-blank@example.com")
    set_id = (await a_set(client, token, await a_station_version(db_session)))["id"]

    for blank in ("", "   "):
        response = await client.patch(
            f"/api/v1/me/station-sets/{set_id}", json={"name": blank}, headers=bearer(token)
        )
        assert response.status_code == 422, response.text

    assert (await client.get(f"/api/v1/me/station-sets/{set_id}", headers=bearer(token))).json()[
        "name"
    ] == "Week one"


# --- deleting ---------------------------------------------------------------


async def test_a_set_nobody_has_sat_in_is_thrown_away(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    token = await a_learner(client, db_session, make_actor, "set-delete@example.com")
    set_id = (await a_set(client, token, await a_station_version(db_session)))["id"]

    deleted = await client.delete(f"/api/v1/me/station-sets/{set_id}", headers=bearer(token))
    assert deleted.status_code == 204, deleted.text

    gone = await client.get(f"/api/v1/me/station-sets/{set_id}", headers=bearer(token))
    assert gone.status_code == 404
    assert gone.json()["code"] == "set_not_found"
    assert (await client.get("/api/v1/me/station-sets", headers=bearer(token))).json()["items"] == []


async def test_deleting_someone_elses_set_is_a_404_and_takes_nothing(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    owner = await a_learner(client, db_session, make_actor, "set-keep-owner@example.com")
    stranger = await a_learner(client, db_session, make_actor, "set-keep-stranger@example.com")
    set_id = (await a_set(client, owner, await a_station_version(db_session)))["id"]

    response = await client.delete(f"/api/v1/me/station-sets/{set_id}", headers=bearer(stranger))
    assert response.status_code == 404
    assert response.json()["code"] == "set_not_found"

    assert (await client.get(f"/api/v1/me/station-sets/{set_id}", headers=bearer(owner))).status_code == 200


async def test_a_set_with_an_attempt_in_it_is_not_deleted(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """The recordings are the reason the delete stops.

    An entry is what a set attempt points at, and a recording of a consultation
    is not something a rename's neighbour deletes on the way past. The retiring
    client threw the session's progress away and left the transcripts behind;
    this refuses rather than either orphaning a recording or erasing one.
    """
    token = await a_learner(client, db_session, make_actor, "set-used@example.com")
    built = await a_set(client, token, await a_station_version(db_session))
    entry_id = built["entries"][0]["id"]
    started = await client.post(
        f"/api/v1/me/station-sets/{built['id']}/entries/{entry_id}/attempts", headers=bearer(token)
    )
    assert started.status_code == 201, started.text

    response = await client.delete(f"/api/v1/me/station-sets/{built['id']}", headers=bearer(token))
    assert response.status_code == 409
    assert response.json()["code"] == "set_has_attempts"

    still_there = await client.get(f"/api/v1/me/station-sets/{built['id']}", headers=bearer(token))
    assert still_there.status_code == 200
    # The delete gate (`set_has_attempts`) is keyed on an attempt row existing against the entry,
    # not on this counter — it refused above even though the attempt was only ever opened, never
    # started, so the counter that only a started consultation moves is still 0.
    assert still_there.json()["entries"][0]["attempts"] == 0


async def test_a_set_whose_station_was_taken_out_of_it_still_deletes(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """An attempt elsewhere for the same station is not this set's business.

    The console's "reset attempts" zeroes an entry's counter and keeps the
    recording, so the counters cannot answer whether a set holds one. This is
    the shape that catches a route that thought they could.
    """
    token = await a_learner(client, db_session, make_actor, "set-twice@example.com")
    version = await a_station_version(db_session)
    first = await a_set(client, token, version, name="First")
    second = await a_set(client, token, version, name="Second")
    started = await client.post(
        f"/api/v1/me/station-sets/{first['id']}/entries/{first['entries'][0]['id']}/attempts",
        headers=bearer(token),
    )
    assert started.status_code == 201, started.text

    response = await client.delete(f"/api/v1/me/station-sets/{second['id']}", headers=bearer(token))
    assert response.status_code == 204, response.text
    assert (
        await client.get(f"/api/v1/me/station-sets/{first['id']}", headers=bearer(token))
    ).status_code == 200
