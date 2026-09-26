"""Building a practice set and working through it."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.features.entitlements import repository as ent_repo
from app.features.entitlements.models import Entitlement
from app.features.identity import repository as identity_repo
from tests.support.catalog import ensure_exam
from tests.support.finished_consultation import finish_consultation
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


def worker_headers() -> dict[str, str]:
    """Auth for `/api/worker/*`, the route the LiveKit worker calls to fetch its attempt.

    A worker fetching this is the one signal that a consultation actually started (see
    `attempts.service_worker.bootstrap`), so it is what these tests call to "start" an attempt
    rather than reaching into the repository to fake the transition.
    """
    settings = get_settings()
    return {settings.worker_secret_header: settings.worker_secret}


async def start(client: AsyncClient, attempt_id: str) -> None:
    """Simulate the worker beginning the consultation, the way a real one does."""
    response = await client.get(f"/api/worker/attempts/{attempt_id}", headers=worker_headers())
    assert response.status_code == 200, response.text


async def a_learner(client: AsyncClient, db_session: AsyncSession, make_actor, email: str) -> str:  # type: ignore[no-untyped-def]
    token = await make_actor(email)
    user = await identity_repo.user_by_email(db_session, email)
    assert user is not None
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    await ent_repo.grant(
        session=db_session,
        user_id=user.id,
        exam_id=exam.id,
        source="purchase",
        ends_at=datetime.now(UTC) + timedelta(days=30),
    )
    await db_session.flush()
    return token


async def a_station_version(db_session: AsyncSession) -> uuid.UUID:
    """A platform-library station, which is what a consumer set draws on."""
    from app.features.stations.models import Station, StationVersion

    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    station = Station(owner_kind="platform", org_id=None, exam_id=exam.id, title="Chest pain")
    db_session.add(station)
    await db_session.flush()
    version = StationVersion(
        station_id=station.id, org_id=None, version=1, content={"x": 1}, status="published"
    )
    db_session.add(version)
    await db_session.flush()
    return version.id


async def test_a_set_is_created_with_its_entries(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    token = await a_learner(client, db_session, make_actor, "s1@example.com")
    version = await a_station_version(db_session)
    response = await client.post(
        "/api/v1/me/station-sets",
        json={"name": "Week one", "exam_code": "sca", "station_version_ids": [str(version)]},
        headers=bearer(token),
    )
    assert response.status_code == 201
    assert response.json()["total_entries"] == 1
    assert response.json()["attempted_entries"] == 0


async def test_opening_an_entry_does_not_count_until_the_consultation_starts(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """Opening a station creates the attempt the brief is read through, but does not spend a go.

    A candidate who opens the page and leaves — never pressing "start consultation" — must not use
    up an attempt they never had. The regression this guards: `station_sets` used to count the
    entry the moment the attempt was created, so a `created` row that never became `running` still
    used up a go against `exam.station_attempt_limit`.
    """
    token = await a_learner(client, db_session, make_actor, "s2@example.com")
    version = await a_station_version(db_session)
    created = (
        await client.post(
            "/api/v1/me/station-sets",
            json={"name": "W", "exam_code": "sca", "station_version_ids": [str(version)]},
            headers=bearer(token),
        )
    ).json()
    entry_id = created["entries"][0]["id"]

    attempt = await client.post(
        f"/api/v1/me/station-sets/{created['id']}/entries/{entry_id}/attempts",
        headers=bearer(token),
    )
    assert attempt.status_code == 201
    assert attempt.json()["kind"] == "set_station"
    # Opened, never started: nothing counted yet.
    assert attempt.json()["attempts_used"] == 0

    opened_only = await client.get(f"/api/v1/me/station-sets/{created['id']}", headers=bearer(token))
    assert opened_only.json()["entries"][0]["attempts"] == 0
    assert opened_only.json()["attempted_entries"] == 0
    assert opened_only.json()["completed_at"] is None

    # The candidate comes back and actually starts the consultation this time.
    await start(client, attempt.json()["attempt_id"])

    started = await client.get(f"/api/v1/me/station-sets/{created['id']}", headers=bearer(token))
    assert started.json()["entries"][0]["attempts"] == 1
    assert started.json()["attempted_entries"] == 1
    assert started.json()["completed_at"] is not None


async def test_the_attempt_limit_is_enforced(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """Three per station, from the exam. b2c enforces this by mutating an array
    on the user document without a transaction.

    Each of the three has to actually start, not just be created: only a started attempt counts
    (see `test_opening_an_entry_does_not_count_until_the_consultation_starts`), so creating and
    abandoning four in a row would wrongly stay under the limit forever.
    """
    token = await a_learner(client, db_session, make_actor, "s3@example.com")
    version = await a_station_version(db_session)
    created = (
        await client.post(
            "/api/v1/me/station-sets",
            json={"name": "W", "exam_code": "sca", "station_version_ids": [str(version)]},
            headers=bearer(token),
        )
    ).json()
    url = f"/api/v1/me/station-sets/{created['id']}/entries/{created['entries'][0]['id']}/attempts"

    for _ in range(3):
        opened = await client.post(url, headers=bearer(token))
        assert opened.status_code == 201, opened.text
        await start(client, opened.json()["attempt_id"])
    refused = await client.post(url, headers=bearer(token))
    assert refused.status_code == 409
    assert refused.json()["code"] == "attempt_limit_reached"


async def test_someone_elses_set_is_not_found(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """404 rather than 403: a set id is not something a stranger should be able
    to confirm exists."""
    token = await a_learner(client, db_session, make_actor, "s4@example.com")
    version = await a_station_version(db_session)
    created = (
        await client.post(
            "/api/v1/me/station-sets",
            json={"name": "W", "exam_code": "sca", "station_version_ids": [str(version)]},
            headers=bearer(token),
        )
    ).json()
    stranger = await make_actor("s4-other@example.com")
    response = await client.get(f"/api/v1/me/station-sets/{created['id']}", headers=bearer(stranger))
    assert response.status_code == 404
    assert response.json()["code"] == "set_not_found"


async def test_a_set_cannot_be_built_for_an_exam_you_do_not_hold(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """Refused when the session is built, not at its first station.

    The gate used to sit only on the attempt, so somebody without access could
    name a session, pick its stations and be turned away at the first one — a
    dead end the client walks them into rather than a refusal it can explain.

    Aged past the trial window on purpose. A brand-new account is exactly who
    the free trial is for, and this route honours it.
    """
    from sqlalchemy import update

    from app.features.identity.models import User

    token = await make_actor("s5@example.com")
    await db_session.execute(
        update(User)
        .where(User.email == "s5@example.com")
        .values(created_at=datetime.now(UTC) - timedelta(days=30))
    )
    await db_session.flush()
    version = await a_station_version(db_session)

    response = await client.post(
        "/api/v1/me/station-sets",
        json={"name": "W", "exam_code": "sca", "station_version_ids": [str(version)]},
        headers=bearer(token),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "not_entitled"


async def test_a_set_built_before_access_lapsed_cannot_be_attempted(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """The set is still the learner's; running a station needs access now.

    The realistic case for the gate on the attempt: a subscriber builds a
    session, their subscription ends, and the session is still sitting there.
    Revoking does not delete the entitlement row, so the refusal depends on
    `live` rather than on the row's absence.
    """
    from sqlalchemy import update

    from app.features.entitlements.models import Entitlement
    from app.features.identity.models import User

    token = await a_learner(client, db_session, make_actor, "lapsing@example.com")
    version = await a_station_version(db_session)
    created = (
        await client.post(
            "/api/v1/me/station-sets",
            json={"name": "W", "exam_code": "sca", "station_version_ids": [str(version)]},
            headers=bearer(token),
        )
    ).json()
    assert "id" in created, created

    # Their subscription ends, and the account is too old for the trial to
    # catch them.
    user = await identity_repo.user_by_email(db_session, "lapsing@example.com")
    assert user is not None
    await db_session.execute(
        update(Entitlement)
        .where(Entitlement.user_id == user.id)
        .values(ends_at=datetime.now(UTC) - timedelta(days=1))
    )
    await db_session.execute(
        update(User)
        .where(User.email == "lapsing@example.com")
        .values(created_at=datetime.now(UTC) - timedelta(days=30))
    )
    await db_session.flush()

    response = await client.post(
        f"/api/v1/me/station-sets/{created['id']}/entries/{created['entries'][0]['id']}/attempts",
        headers=bearer(token),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "not_entitled"


async def test_a_debrief_can_be_started_from_an_entry(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """`start_entry_attempt(debrief=True)` was written, tested and unreachable.

    The b2c debrief — talking an attempt through afterwards — had no route at
    all, so the only way to reach the code was to call the service directly.
    """
    token = await a_learner(client, db_session, make_actor, "debrief@example.com")
    version = await a_station_version(db_session)
    created = (
        await client.post(
            "/api/v1/me/station-sets",
            json={"name": "W", "exam_code": "sca", "station_version_ids": [str(version)]},
            headers=bearer(token),
        )
    ).json()
    set_id, entry_id = created["id"], created["entries"][0]["id"]

    nothing_yet = await client.post(
        f"/api/v1/me/station-sets/{set_id}/entries/{entry_id}/debriefs", headers=bearer(token)
    )
    assert nothing_yet.status_code == 409, nothing_yet.text
    assert nothing_yet.json()["code"] == "nothing_to_debrief"

    attempt = await client.post(
        f"/api/v1/me/station-sets/{set_id}/entries/{entry_id}/attempts", headers=bearer(token)
    )
    assert attempt.status_code == 201, attempt.text
    # Started, not merely opened: `ensure_debriefable` now refuses on `entry.attempts`, which only
    # counts a consultation that actually began (see
    # `test_opening_an_entry_does_not_count_until_the_consultation_starts`).
    await start(client, attempt.json()["attempt_id"])
    await finish_consultation(db_session, uuid.UUID(attempt.json()["attempt_id"]))

    debrief = await client.post(
        f"/api/v1/me/station-sets/{set_id}/entries/{entry_id}/debriefs", headers=bearer(token)
    )
    assert debrief.status_code == 201, debrief.text
    assert debrief.json()["kind"] == "debrief"


async def test_feedback_is_not_ready_until_the_newest_attempt_is_marked(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """A station last sat is not the same as a station last marked.

    `finish_consultation` only drives an attempt to `interaction_complete` —
    sat, not yet scored — so a set whose only station reached that far must
    still say `feedback_ready: false`, both on the entry and on the set as a
    whole. Only once the attempt is `evaluated` does either flip to `true`.
    """
    from app.features.attempts import repository as attempts_repo
    from app.features.attempts.domain import Status

    token = await a_learner(client, db_session, make_actor, "feedback-pending@example.com")
    version = await a_station_version(db_session)
    created = (
        await client.post(
            "/api/v1/me/station-sets",
            json={"name": "W", "exam_code": "sca", "station_version_ids": [str(version)]},
            headers=bearer(token),
        )
    ).json()
    assert created["feedback_ready"] is False
    assert created["entries"][0]["feedback_ready"] is False
    assert created["entries"][0]["last_attempt_status"] is None

    set_id, entry_id = created["id"], created["entries"][0]["id"]
    attempt = await client.post(
        f"/api/v1/me/station-sets/{set_id}/entries/{entry_id}/attempts", headers=bearer(token)
    )
    attempt_id = uuid.UUID(attempt.json()["attempt_id"])
    await start(client, str(attempt_id))
    await finish_consultation(db_session, attempt_id)

    sat_not_marked = await client.get(f"/api/v1/me/station-sets/{set_id}", headers=bearer(token))
    assert sat_not_marked.json()["feedback_ready"] is False
    assert sat_not_marked.json()["entries"][0]["feedback_ready"] is False
    assert sat_not_marked.json()["entries"][0]["last_attempt_status"] == "interaction_complete"

    await attempts_repo.set_status(db_session, attempt_id, status=Status.EVALUATED, at=datetime.now(UTC))
    await db_session.flush()

    marked = await client.get(f"/api/v1/me/station-sets/{set_id}", headers=bearer(token))
    assert marked.json()["feedback_ready"] is True
    assert marked.json()["entries"][0]["feedback_ready"] is True
    assert marked.json()["entries"][0]["last_attempt_status"] == "evaluated"


async def test_feedback_ready_is_a_set_wide_flag_from_any_one_entry(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """One marked station out of several is enough to show the badge on the set.

    A learner works through a session station by station, and each one is
    marked on its own schedule — waiting for every station before saying
    anything would hide feedback that is already sitting there for the first.
    """
    from app.features.attempts import repository as attempts_repo
    from app.features.attempts.domain import Status

    token = await a_learner(client, db_session, make_actor, "feedback-partial@example.com")
    version_a = await a_station_version(db_session)
    version_b = await a_station_version(db_session)
    created = (
        await client.post(
            "/api/v1/me/station-sets",
            json={
                "name": "W",
                "exam_code": "sca",
                "station_version_ids": [str(version_a), str(version_b)],
            },
            headers=bearer(token),
        )
    ).json()
    set_id = created["id"]
    first_entry_id = created["entries"][0]["id"]

    attempt = await client.post(
        f"/api/v1/me/station-sets/{set_id}/entries/{first_entry_id}/attempts", headers=bearer(token)
    )
    attempt_id = uuid.UUID(attempt.json()["attempt_id"])
    await start(client, str(attempt_id))
    await finish_consultation(db_session, attempt_id)
    await attempts_repo.set_status(db_session, attempt_id, status=Status.EVALUATED, at=datetime.now(UTC))
    await db_session.flush()

    read_back = await client.get(f"/api/v1/me/station-sets/{set_id}", headers=bearer(token))
    body = read_back.json()
    assert body["feedback_ready"] is True
    entries_by_id = {entry["id"]: entry for entry in body["entries"]}
    assert entries_by_id[first_entry_id]["feedback_ready"] is True
    other_entry_id = next(e["id"] for e in body["entries"] if e["id"] != first_entry_id)
    assert entries_by_id[other_entry_id]["feedback_ready"] is False
    assert entries_by_id[other_entry_id]["last_attempt_status"] is None


async def test_a_debrief_does_not_recheck_exam_access_after_the_source_attempt(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    token = await a_learner(client, db_session, make_actor, "debrief-expired@example.com")
    user = await identity_repo.user_by_email(db_session, "debrief-expired@example.com")
    assert user is not None
    version = await a_station_version(db_session)
    created = (
        await client.post(
            "/api/v1/me/station-sets",
            json={"name": "W", "exam_code": "sca", "station_version_ids": [str(version)]},
            headers=bearer(token),
        )
    ).json()
    set_id, entry_id = created["id"], created["entries"][0]["id"]

    attempt = await client.post(
        f"/api/v1/me/station-sets/{set_id}/entries/{entry_id}/attempts", headers=bearer(token)
    )
    assert attempt.status_code == 201, attempt.text
    await start(client, attempt.json()["attempt_id"])
    await finish_consultation(db_session, uuid.UUID(attempt.json()["attempt_id"]))

    await db_session.execute(
        update(Entitlement)
        .where(Entitlement.user_id == user.id)
        .values(ends_at=datetime.now(UTC) - timedelta(days=1))
    )
    await db_session.flush()

    debrief = await client.post(
        f"/api/v1/me/station-sets/{set_id}/entries/{entry_id}/debriefs", headers=bearer(token)
    )
    assert debrief.status_code == 201, debrief.text
    assert debrief.json()["kind"] == "debrief"
