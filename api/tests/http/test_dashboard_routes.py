"""One request for a screen that currently makes seven."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.features.entitlements import repository as ent_repo
from app.features.identity import repository as identity_repo
from tests.support.catalog import ensure_exam
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def start(client: AsyncClient, attempt_id: str) -> None:
    """Simulate a worker actually starting a consultation — see
    `tests.http.test_station_sets_routes.start`. A practice-set entry only
    counts as attempted once this happens, not merely once the attempt exists.
    """
    settings = get_settings()
    response = await client.get(
        f"/api/worker/attempts/{attempt_id}",
        headers={settings.worker_secret_header: settings.worker_secret},
    )
    assert response.status_code == 200, response.text


async def a_learner(db_session: AsyncSession, make_actor, email: str) -> str:  # type: ignore[no-untyped-def]
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
    from app.features.stations.models import Station, StationVersion

    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    station = Station(owner_kind="platform", org_id=None, exam_id=exam.id, title="S")
    db_session.add(station)
    await db_session.flush()
    version = StationVersion(station_id=station.id, org_id=None, version=1, content={}, status="published")
    db_session.add(version)
    await db_session.flush()
    return version.id


async def test_an_empty_dashboard_is_still_a_dashboard(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """A new account gets a shape it can render, not a 404."""
    token = await make_actor("d0@example.com")
    response = await client.get("/api/v1/me/dashboard", headers=bearer(token))
    assert response.status_code == 200
    body = response.json()
    assert body["entitlements"] == []
    assert body["progress"] == []
    assert body["recent_attempts"] == []


async def test_the_dashboard_shows_access_progress_and_sets(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    token = await a_learner(db_session, make_actor, "d1@example.com")
    version = await a_station_version(db_session)

    created = (
        await client.post(
            "/api/v1/me/station-sets",
            json={"name": "Week one", "exam_code": "sca", "station_version_ids": [str(version)]},
            headers=bearer(token),
        )
    ).json()
    opened = await client.post(
        f"/api/v1/me/station-sets/{created['id']}/entries/{created['entries'][0]['id']}/attempts",
        headers=bearer(token),
    )
    # The set entry's counter only moves once the consultation actually starts, not merely once
    # the attempt row exists — see `station_sets.service.start_entry_attempt`.
    await start(client, opened.json()["attempt_id"])

    response = await client.get("/api/v1/me/dashboard", headers=bearer(token))
    body = response.json()

    assert [e["exam_code"] for e in body["entitlements"]] == ["sca"]
    assert body["entitlements"][0]["live"] is True
    assert body["progress"][0] == {
        "exam_code": "sca",
        "attempts": 1,
        "evaluated": 0,
        "last_attempt_at": body["progress"][0]["last_attempt_at"],
    }
    assert body["recent_attempts"][0]["kind"] == "set_station"
    assert body["recent_attempts"][0]["has_result"] is False
    assert body["sets"][0]["attempted_entries"] == 1


async def test_the_dashboard_is_only_your_own(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    await a_learner(db_session, make_actor, "d2@example.com")
    other = await make_actor("d2-other@example.com")
    response = await client.get("/api/v1/me/dashboard", headers=bearer(other))
    assert response.json()["entitlements"] == []


async def test_the_dashboard_needs_a_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/me/dashboard")
    assert response.status_code == 401


async def test_the_dashboard_says_which_exams_may_be_opened(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """One answer, so no screen has to guess.

    Four screens each derived their own from a different source — attempts, the
    whole catalogue, whichever exam sorted first — and offered a picker over
    exams nobody had bought.
    """
    token = await a_learner(db_session, make_actor, "exams@example.com")
    await db_session.commit()

    response = await client.get("/api/v1/me/dashboard", headers=bearer(token))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["exam_codes"] == ["sca"]
    assert body["current_exam_code"] == "sca"


async def test_a_lapsed_subscriber_is_offered_no_exam(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """Revoking does not delete, so the row is still on `/me/entitlements`.

    Reading exam codes off that list without checking `live` is what would give
    a lapsed subscriber the same library as a paying one.
    """
    token = await make_actor("lapsed@example.com")
    user = await identity_repo.user_by_email(db_session, "lapsed@example.com")
    assert user is not None
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    await ent_repo.grant(
        session=db_session,
        user_id=user.id,
        exam_id=exam.id,
        source="purchase",
        ends_at=datetime.now(UTC) - timedelta(days=1),
    )
    await db_session.commit()

    body = (await client.get("/api/v1/me/dashboard", headers=bearer(token))).json()

    assert body["entitlements"], "the expired row is still reported"
    assert body["entitlements"][0]["live"] is False
    assert body["exam_codes"] == []
    assert body["current_exam_code"] is None


async def test_a_trial_account_opens_on_the_exam_it_signed_up_for(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """Somebody inside their free trial holds no grant at all."""
    from sqlalchemy import update

    from app.features.identity.models import User

    token = await make_actor("trial@example.com")
    await ensure_exam(db_session, "plab")
    await db_session.execute(update(User).where(User.email == "trial@example.com").values(exam_code="plab"))
    await db_session.commit()

    body = (await client.get("/api/v1/me/dashboard", headers=bearer(token))).json()

    assert body["exam_codes"] == ["plab"]
    assert body["current_exam_code"] == "plab"


async def test_the_dashboard_carries_the_current_exam_and_its_settings(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """The home screen's date label and modes come from the exam row, so it needs no exam-code switch."""
    token = await a_learner(db_session, make_actor, "d-settings@example.com")
    body = (await client.get("/api/v1/me/dashboard", headers=bearer(token))).json()
    assert body["current_exam_code"] == "sca"
    assert body["current_exam"]["code"] == "sca"
    assert body["current_exam"]["name"] == "SCA"
    assert body["current_exam"]["settings"]["date_label"] == "Exam date"
    assert body["current_exam"]["settings"]["session_modes"] == ["debrief", "practice_as_patient"]


async def test_a_new_account_has_no_current_exam(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("d-no-exam@example.com")
    body = (await client.get("/api/v1/me/dashboard", headers=bearer(token))).json()
    assert body["current_exam"] is None
