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

from tests.http.test_station_sets_routes import a_learner, a_station_version, start
from tests.support.catalog import ensure_exam
from tests.support.finished_consultation import finish_consultation
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


# --- replacing a set's stations (the legacy "edit session" screen) ---------


async def test_a_learner_swaps_a_set_stations(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """Legacy's edit screen enforced no minimum or maximum station count, so
    neither does this: a set of one station becomes a set of two others."""
    token = await a_learner(client, db_session, make_actor, "swap@example.com")
    original = await a_station_version(db_session)
    replacement_a = await a_station_version(db_session)
    replacement_b = await a_station_version(db_session)
    set_id = (await a_set(client, token, original))["id"]

    updated = await client.patch(
        f"/api/v1/me/station-sets/{set_id}",
        json={
            "name": "Week one",
            "station_version_ids": [str(replacement_b), str(replacement_a)],
        },
        headers=bearer(token),
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["total_entries"] == 2
    # The given order is the stored order.
    assert [e["station_version_id"] for e in body["entries"]] == [
        str(replacement_b),
        str(replacement_a),
    ]
    assert [e["position"] for e in body["entries"]] == [0, 1]


async def test_swapping_stations_on_a_locked_set_is_refused(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    from sqlalchemy import update
    from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSession  # noqa: F401

    from app.features.station_sets.models import StationSet

    token = await a_learner(client, db_session, make_actor, "swap-locked@example.com")
    version = await a_station_version(db_session)
    other = await a_station_version(db_session)
    set_id = (await a_set(client, token, version))["id"]
    await db_session.execute(update(StationSet).where(StationSet.id == uuid.UUID(set_id)).values(locked=True))
    await db_session.flush()

    response = await client.patch(
        f"/api/v1/me/station-sets/{set_id}",
        json={"name": "Week one", "station_version_ids": [str(other)]},
        headers=bearer(token),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "set_locked"


async def test_swapping_in_an_unpublished_station_is_refused(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    from app.features.stations.models import Station, StationVersion

    token = await a_learner(client, db_session, make_actor, "swap-draft@example.com")
    version = await a_station_version(db_session)
    set_id = (await a_set(client, token, version))["id"]
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    draft_station = Station(owner_kind="platform", org_id=None, exam_id=exam.id, title="Draft one")
    db_session.add(draft_station)
    await db_session.flush()
    draft_version = StationVersion(
        station_id=draft_station.id, org_id=None, version=1, content={"x": 1}, status="draft"
    )
    db_session.add(draft_version)
    await db_session.flush()

    response = await client.patch(
        f"/api/v1/me/station-sets/{set_id}",
        json={"name": "Week one", "station_version_ids": [str(draft_version.id)]},
        headers=bearer(token),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "station_version_not_usable"


async def test_swapping_in_an_unknown_station_is_refused(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    token = await a_learner(client, db_session, make_actor, "swap-unknown@example.com")
    version = await a_station_version(db_session)
    set_id = (await a_set(client, token, version))["id"]

    response = await client.patch(
        f"/api/v1/me/station-sets/{set_id}",
        json={"name": "Week one", "station_version_ids": [str(uuid.uuid4())]},
        headers=bearer(token),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "station_version_not_usable"


async def test_swapping_in_a_station_from_another_exam_is_refused(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    from app.features.stations.models import Station, StationVersion

    token = await a_learner(client, db_session, make_actor, "swap-otherexam@example.com")
    version = await a_station_version(db_session)
    set_id = (await a_set(client, token, version))["id"]
    other_exam = await ensure_exam(db_session, "misra")
    assert other_exam is not None
    other_station = Station(owner_kind="platform", org_id=None, exam_id=other_exam.id, title="Other exam")
    db_session.add(other_station)
    await db_session.flush()
    other_version = StationVersion(
        station_id=other_station.id, org_id=None, version=1, content={"x": 1}, status="published"
    )
    db_session.add(other_version)
    await db_session.flush()

    response = await client.patch(
        f"/api/v1/me/station-sets/{set_id}",
        json={"name": "Week one", "station_version_ids": [str(other_version.id)]},
        headers=bearer(token),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "station_version_not_usable"


async def test_a_station_kept_in_the_swap_keeps_its_attempt_counter(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """A station that stays in the set is the same entry, not a fresh one.

    Its attempt counter is what an attempt points at (`RESTRICT`): swapping in
    a second station alongside it must not reset what the learner already sat.
    """
    token = await a_learner(client, db_session, make_actor, "swap-keep@example.com")
    kept = await a_station_version(db_session)
    added = await a_station_version(db_session)
    built = await a_set(client, token, kept)
    set_id, kept_entry_id = built["id"], built["entries"][0]["id"]

    attempt = await client.post(
        f"/api/v1/me/station-sets/{set_id}/entries/{kept_entry_id}/attempts", headers=bearer(token)
    )
    assert attempt.status_code == 201, attempt.text
    await start(client, attempt.json()["attempt_id"])

    updated = await client.patch(
        f"/api/v1/me/station-sets/{set_id}",
        json={"name": "Week one", "station_version_ids": [str(kept), str(added)]},
        headers=bearer(token),
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    kept_after = next(e for e in body["entries"] if e["station_version_id"] == str(kept))
    assert kept_after["id"] == kept_entry_id
    assert kept_after["attempts"] == 1


async def test_removing_a_station_with_no_attempts_succeeds(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    token = await a_learner(client, db_session, make_actor, "swap-remove@example.com")
    to_remove = await a_station_version(db_session)
    to_keep = await a_station_version(db_session)
    built = await a_set(
        client,
        token,
        to_remove,
        name="Week one",
    )
    set_id = built["id"]
    add_second = await client.patch(
        f"/api/v1/me/station-sets/{set_id}",
        json={"name": "Week one", "station_version_ids": [str(to_remove), str(to_keep)]},
        headers=bearer(token),
    )
    assert add_second.status_code == 200, add_second.text

    removed = await client.patch(
        f"/api/v1/me/station-sets/{set_id}",
        json={"name": "Week one", "station_version_ids": [str(to_keep)]},
        headers=bearer(token),
    )
    assert removed.status_code == 200, removed.text
    assert [e["station_version_id"] for e in removed.json()["entries"]] == [str(to_keep)]


async def test_removing_a_station_that_has_an_attempt_is_refused(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """The entry is what the attempt points at, and cannot be dropped out from under it.

    Same shape as `set_has_attempts` on a whole-set delete, but its own code:
    here only one station in the set is in the way, not the set itself.
    """
    token = await a_learner(client, db_session, make_actor, "swap-refuse@example.com")
    to_remove = await a_station_version(db_session)
    to_keep = await a_station_version(db_session)
    built = await a_set(client, token, to_remove)
    set_id, entry_id = built["id"], built["entries"][0]["id"]
    attempt = await client.post(
        f"/api/v1/me/station-sets/{set_id}/entries/{entry_id}/attempts", headers=bearer(token)
    )
    assert attempt.status_code == 201, attempt.text
    attempt_id = uuid.UUID(attempt.json()["attempt_id"])
    await start(client, str(attempt_id))
    await finish_consultation(db_session, attempt_id)

    response = await client.patch(
        f"/api/v1/me/station-sets/{set_id}",
        json={"name": "Week one", "station_version_ids": [str(to_keep)]},
        headers=bearer(token),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "set_entry_has_attempts"

    unchanged = await client.get(f"/api/v1/me/station-sets/{set_id}", headers=bearer(token))
    assert [e["station_version_id"] for e in unchanged.json()["entries"]] == [str(to_remove)]


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
