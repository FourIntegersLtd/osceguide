"""One person's station progress, and the two things the old console did to it.

The B2C admin listed `station_progress` per user with an attempt counter, a
"reset attempts" button and a "delete station" button. Here the counter is a
practice set's entry and the record is the attempt, so each test builds both
the way a learner does — a set, an entry, an attempt — and checks the console
reads and changes them together.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import repository as attempts_repo
from app.features.identity import repository as identity_repo
from tests.contract.test_worker_routes import worker_headers
from tests.http.test_station_sets_routes import a_learner, a_station_version, start
from tests.support.finished_consultation import finish_consultation
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def a_learner_with_a_sat_station(client: AsyncClient, db_session: AsyncSession, make_actor, email: str):  # type: ignore[no-untyped-def]
    """A person, their set, its entry and two attempts at one station.

    Each one is actually started, not merely opened — the practice-set entry's own counter
    (`entry_attempts` below) only moves once a worker fetches the attempt, and this fixture's name
    says these two were sat, not just begun and abandoned.
    """
    token = await a_learner(client, db_session, make_actor, email)
    user = await identity_repo.user_by_email(db_session, email)
    assert user is not None
    version = await a_station_version(db_session)
    created = (
        await client.post(
            "/api/v1/me/station-sets",
            json={"name": "W", "exam_code": "sca", "station_version_ids": [str(version)]},
            headers=bearer(token),
        )
    ).json()
    url = f"/api/v1/me/station-sets/{created['id']}/entries/{created['entries'][0]['id']}/attempts"
    attempt_ids = []
    for _ in range(2):
        opened = await client.post(url, headers=bearer(token))
        assert opened.status_code == 201, opened.text
        await start(client, opened.json()["attempt_id"])
        attempt_ids.append(opened.json()["attempt_id"])
    return token, user.id, created, url, attempt_ids


async def station_id_of(db_session: AsyncSession, attempt_id: str) -> uuid.UUID:
    from app.features.stations.models import StationVersion

    attempt = await attempts_repo.attempt_by_id(db_session, uuid.UUID(attempt_id))
    assert attempt is not None and attempt.station_version_id is not None
    version = await db_session.get(StationVersion, attempt.station_version_id)
    assert version is not None
    return version.station_id


async def test_progress_is_one_row_per_station_with_both_counts(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    _, user_id, created, _, attempt_ids = await a_learner_with_a_sat_station(
        client, db_session, make_actor, "p@example.com"
    )

    listed = await client.get(f"/api/v1/platform/users/{user_id}/stations", headers=bearer(root))
    assert listed.status_code == 200, listed.text
    [row] = listed.json()
    assert row["title"] == "Chest pain"
    assert row["exam_code"] == "sca"
    assert row["attempts"] == 2
    assert row["evaluated"] == 0
    assert row["entry_attempts"] == 2
    assert row["set_entry_ids"] == [created["entries"][0]["id"]]
    # Both attempts are written in this fixture's one transaction, so they
    # share a `created_at` and "newest" falls to the documented tie-break —
    # greater id wins (`attempts.repository_platform.progress_by_version`).
    assert row["last_attempt_id"] == max(attempt_ids)
    assert row["last_status"] == "running"
    assert row["last_attempt_at"] is not None

    nobody = await client.get(f"/api/v1/platform/users/{uuid.uuid4()}/stations", headers=bearer(root))
    assert nobody.status_code == 404
    assert nobody.json()["code"] == "user_not_found"


async def test_reset_zeroes_the_counters_and_keeps_the_attempts(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Exactly the old console's act: the limit opens again, the record stays."""
    root = await make_actor("root@osceguide.com", platform_admin=True)
    token, user_id, created, url, attempt_ids = await a_learner_with_a_sat_station(
        client, db_session, make_actor, "r@example.com"
    )
    third = await client.post(url, headers=bearer(token))
    assert third.status_code == 201, third.text
    # The third has to actually start too, or the entry's counter never reaches the limit and the
    # next request would wrongly be allowed through.
    await start(client, third.json()["attempt_id"])
    assert (await client.post(url, headers=bearer(token))).json()["code"] == "attempt_limit_reached"
    station_id = await station_id_of(db_session, attempt_ids[0])

    reset = await client.post(
        f"/api/v1/platform/users/{user_id}/stations/{station_id}/reset-attempts", headers=bearer(root)
    )
    assert reset.status_code == 200, reset.text
    assert reset.json() == {
        "station_id": str(station_id),
        "attempts_deleted": 0,
        "entries_reset": 1,
        "entries_removed": 0,
    }

    [row] = (await client.get(f"/api/v1/platform/users/{user_id}/stations", headers=bearer(root))).json()
    assert row["attempts"] == 3
    assert row["entry_attempts"] == 0
    refreshed = await client.get(f"/api/v1/me/station-sets/{created['id']}", headers=bearer(token))
    assert refreshed.json()["entries"][0]["attempts"] == 0
    assert (await client.post(url, headers=bearer(token))).status_code == 201

    audit = await client.get(
        "/api/v1/platform/audit?action=user.station_attempts_reset", headers=bearer(root)
    )
    [entry] = [row for row in audit.json()["items"] if row["target_id"] == str(user_id)]
    assert entry["summary"] == "Chest pain"
    assert entry["meta"]["entries_reset"] == 1


async def test_delete_removes_the_attempts_and_the_entries_and_is_audited(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    token, user_id, created, _, attempt_ids = await a_learner_with_a_sat_station(
        client, db_session, make_actor, "d@example.com"
    )
    # Both attempts are actually running (see `a_learner_with_a_sat_station`), and a delete refuses
    # while one is: the room would be pulled out from under the worker mid-consultation. Take each
    # to a finished state first, the way a real one would end before anyone asks to delete it.
    for attempt_id in attempt_ids:
        await finish_consultation(db_session, uuid.UUID(attempt_id))
    station_id = await station_id_of(db_session, attempt_ids[0])

    deleted = await client.post(
        f"/api/v1/platform/users/{user_id}/stations/{station_id}/delete-progress",
        json={"reason": "Asked to start over"},
        headers=bearer(root),
    )
    assert deleted.status_code == 200, deleted.text
    assert deleted.json() == {
        "station_id": str(station_id),
        "attempts_deleted": 2,
        "entries_reset": 0,
        "entries_removed": 1,
    }

    assert (await client.get(f"/api/v1/platform/users/{user_id}/stations", headers=bearer(root))).json() == []
    for attempt_id in attempt_ids:
        gone = await client.get(f"/api/v1/platform/attempts/{attempt_id}", headers=bearer(root))
        assert gone.status_code == 404
    refreshed = await client.get(f"/api/v1/me/station-sets/{created['id']}", headers=bearer(token))
    assert refreshed.json()["entries"] == []

    audit = await client.get(
        "/api/v1/platform/audit?action=user.station_progress_deleted", headers=bearer(root)
    )
    [entry] = [row for row in audit.json()["items"] if row["target_id"] == str(user_id)]
    assert entry["summary"] == "Chest pain: Asked to start over"
    assert entry["meta"]["attempts_deleted"] == 2

    unknown = await client.post(
        f"/api/v1/platform/users/{user_id}/stations/{uuid.uuid4()}/delete-progress",
        json={"reason": "x"},
        headers=bearer(root),
    )
    assert unknown.status_code == 404
    assert unknown.json()["code"] == "station_not_found"


async def test_delete_is_refused_while_an_attempt_is_running(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    _, user_id, _, _, attempt_ids = await a_learner_with_a_sat_station(
        client, db_session, make_actor, "live@example.com"
    )
    station_id = await station_id_of(db_session, attempt_ids[0])
    running = await client.get(f"/api/worker/attempts/{attempt_ids[-1]}", headers=worker_headers())
    assert running.status_code == 200, running.text

    refused = await client.post(
        f"/api/v1/platform/users/{user_id}/stations/{station_id}/delete-progress",
        json={"reason": "x"},
        headers=bearer(root),
    )
    assert refused.status_code == 409
    assert refused.json()["code"] == "attempt_in_progress"
    assert (
        len((await client.get(f"/api/v1/platform/users/{user_id}/stations", headers=bearer(root))).json())
        == 1
    )


async def test_the_station_routes_are_the_consoles_alone(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    token, user_id, _, _, attempt_ids = await a_learner_with_a_sat_station(
        client, db_session, make_actor, "me@example.com"
    )
    station_id = await station_id_of(db_session, attempt_ids[0])
    base = f"/api/v1/platform/users/{user_id}/stations"
    assert (await client.get(base, headers=bearer(token))).status_code == 403
    assert (
        await client.post(f"{base}/{station_id}/reset-attempts", headers=bearer(token))
    ).status_code == 403
    assert (
        await client.post(f"{base}/{station_id}/delete-progress", json={"reason": "x"}, headers=bearer(token))
    ).status_code == 403
