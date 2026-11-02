"""A plan's `station_limit` narrows the library to a window of stations, and the date floor
hides anything first published before the old site started showing library stations.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.billing import repository as billing_repo
from app.features.entitlements import repository as entitlements_repo
from app.features.identity import repository as identity_repo
from app.features.stations.models import Station, StationVersion
from tests.http.test_billing_routes import a_customer, checkout_event, post_event
from tests.support.catalog import ensure_exam
from tests.support.fakes import FIXED_NOW
from tests.support.tokens import bearer, mint_token

pytestmark = pytest.mark.db


async def _station(
    db_session: AsyncSession, *, title: str, exam_id: uuid.UUID, published_at: datetime
) -> uuid.UUID:
    """A published platform-library station, first published at a chosen moment."""
    station = Station(
        owner_kind="platform",
        org_id=None,
        exam_id=exam_id,
        title=title,
        status="published",
        # An editor's approval, on top of status: this helper models a station already live in
        # the library, which the plan window then narrows.
        approved=True,
    )
    db_session.add(station)
    await db_session.flush()
    version = StationVersion(
        station_id=station.id,
        org_id=None,
        version=1,
        content={"patient_information": {"persona": "anxious"}},
        status="published",
        published_at=published_at,
    )
    db_session.add(version)
    await db_session.flush()
    station.current_version_id = version.id
    await db_session.flush()
    return station.id


async def _five_stations_and_one_too_old(db_session: AsyncSession) -> tuple[uuid.UUID, list[uuid.UUID]]:
    """An exam with 5 library stations published 2025-03-01..05, plus one from 2024-12-01."""
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    station_ids = [
        await _station(
            db_session,
            title=f"Station {day}",
            exam_id=exam.id,
            published_at=datetime(2025, 3, day, tzinfo=UTC),
        )
        for day in range(1, 6)
    ]
    await _station(
        db_session, title="Too old", exam_id=exam.id, published_at=datetime(2024, 12, 1, tzinfo=UTC)
    )
    return exam.id, station_ids


async def _browser_with_limit(
    client: AsyncClient, db_session: AsyncSession, email: str, *, station_limit: int | None
) -> str:
    """A signed-in SCA consumer who has bought the one plan on offer, with the given limit."""
    from sqlalchemy import update

    from app.features.identity.models import User

    await billing_repo.create_plan(
        db_session,
        code=f"sca_{email.split('@')[0]}",
        stripe_price_id=f"price_{email.split('@')[0]}",
        amount_pence=2499,
        duration_days=365,
        exam_code="sca",
        station_limit=station_limit,
    )
    token = await a_customer_token(client, db_session, email, price_id=f"price_{email.split('@')[0]}")
    await db_session.execute(update(User).where(User.email == email).values(exam_code="sca"))
    await db_session.flush()
    return token


async def a_customer_token(
    client: AsyncClient, db_session: AsyncSession, email: str, *, price_id: str
) -> str:
    """Buy a plan through a real checkout webhook and return the buyer's bearer token."""
    await a_customer(db_session, email)
    response = await post_event(client, checkout_event(f"evt_{email}", email, price_id=price_id))
    assert response.status_code == 200, response.text
    user = await identity_repo.user_by_email(db_session, email)
    assert user is not None
    return mint_token(user_id=user.id, email=email)


async def test_the_too_old_station_is_never_in_the_library(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """The date floor hides a station first published before the old site showed any."""
    exam_id, station_ids = await _five_stations_and_one_too_old(db_session)
    token = await _browser_with_limit(client, db_session, "floor-test@example.com", station_limit=None)

    rows = (await client.get("/api/v1/stations?exam_code=sca", headers=bearer(token))).json()["items"]

    assert {row["title"] for row in rows} == {f"Station {day}" for day in range(1, 6)}
    assert "Too old" not in {row["title"] for row in rows}


async def test_a_limit_of_two_shows_exactly_the_first_two(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """A plan limit of 2 narrows the library to the two earliest-published stations."""
    await _five_stations_and_one_too_old(db_session)
    token = await _browser_with_limit(client, db_session, "limited@example.com", station_limit=2)

    rows = (await client.get("/api/v1/stations?exam_code=sca", headers=bearer(token))).json()["items"]

    assert {row["title"] for row in rows} == {"Station 1", "Station 2"}


async def test_an_attempted_station_stays_visible_once_the_limit_tightens(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Lowering a plan's limit after someone has already attempted a later station does not
    hide the work they have already done; only a station never reached is now out of bounds."""
    exam_id, station_ids = await _five_stations_and_one_too_old(db_session)
    _ = exam_id
    token = await _browser_with_limit(client, db_session, "attempted@example.com", station_limit=5)

    rows = (await client.get("/api/v1/stations?exam_code=sca", headers=bearer(token))).json()["items"]
    version_by_title = {row["title"]: row["version_id"] for row in rows}
    started = await client.post(
        "/api/v1/attempts",
        json={
            "kind": "practice",
            "exam_code": "sca",
            "station_version_id": version_by_title["Station 5"],
        },
        headers=bearer(token),
    )
    assert started.status_code == 201, started.text

    await billing_repo.set_plans_station_limit(db_session, ["sca_attempted"], station_limit=2)

    after = (await client.get("/api/v1/stations?exam_code=sca", headers=bearer(token))).json()["items"]
    assert {row["title"] for row in after} == {"Station 1", "Station 2", "Station 5"}

    blocked = await client.get(f"/api/v1/stations/{station_ids[3]}", headers=bearer(token))
    assert blocked.status_code == 403, blocked.text
    assert blocked.json()["code"] == "station_not_in_plan"

    allowed = await client.get(f"/api/v1/stations/{station_ids[0]}", headers=bearer(token))
    assert allowed.status_code == 200, allowed.text


async def test_starting_a_station_outside_the_window_is_refused(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Starting a station the plan does not unlock is a 403 `station_not_in_plan`, even though the
    first two are never shown as refused — they are simply left off the list."""
    exam_id, station_ids = await _five_stations_and_one_too_old(db_session)
    token = await _browser_with_limit(client, db_session, "blocked@example.com", station_limit=2)

    blocked = await client.get(f"/api/v1/stations/{station_ids[3]}", headers=bearer(token))
    assert blocked.status_code == 403, blocked.text
    assert blocked.json()["code"] == "station_not_in_plan"

    allowed = await client.get(f"/api/v1/stations/{station_ids[0]}", headers=bearer(token))
    assert allowed.status_code == 200, allowed.text


async def test_clearing_the_limit_shows_every_station(client: AsyncClient, db_session: AsyncSession) -> None:
    """Setting `station_limit` back to NULL on the plan removes the window entirely."""
    await _five_stations_and_one_too_old(db_session)
    token = await _browser_with_limit(client, db_session, "cleared@example.com", station_limit=2)
    before = (await client.get("/api/v1/stations?exam_code=sca", headers=bearer(token))).json()["items"]
    assert len(before) == 2

    admin = await identity_repo.user_by_email(db_session, "cleared@example.com")
    assert admin is not None
    plan = await billing_repo.plan_by_code(db_session, "sca_cleared")
    assert plan is not None
    await billing_repo.set_plans_station_limit(db_session, [plan.code], station_limit=None)

    after = (await client.get("/api/v1/stations?exam_code=sca", headers=bearer(token))).json()["items"]
    assert len(after) == 5


async def test_a_trial_only_user_sees_every_station(client: AsyncClient, db_session: AsyncSession) -> None:
    """A trial-only user holds no purchase, so no plan limit ever applies to them."""
    from sqlalchemy import update

    from app.features.identity.models import User

    await _five_stations_and_one_too_old(db_session)
    await billing_repo.create_plan(
        db_session,
        code="sca_trialcap",
        stripe_price_id="price_trialcap",
        amount_pence=2499,
        duration_days=365,
        exam_code="sca",
        station_limit=2,
    )
    await a_customer(db_session, "trial-only@example.com")
    user = await identity_repo.user_by_email(db_session, "trial-only@example.com")
    assert user is not None
    await db_session.execute(
        update(User).where(User.email == "trial-only@example.com").values(exam_code="sca")
    )
    await db_session.flush()
    token = mint_token(user_id=user.id, email="trial-only@example.com")

    rows = (await client.get("/api/v1/stations?exam_code=sca", headers=bearer(token))).json()["items"]

    assert len(rows) == 5


async def test_an_org_grant_user_sees_every_station(client: AsyncClient, db_session: AsyncSession) -> None:
    """An org grant is never capped by a plan's station limit (ADR 0012)."""
    from sqlalchemy import update

    from app.features.catalog import repository as catalog_repo
    from app.features.identity.models import User

    exam_id, _ = await _five_stations_and_one_too_old(db_session)
    await billing_repo.create_plan(
        db_session,
        code="sca_orgcap",
        stripe_price_id="price_orgcap",
        amount_pence=2499,
        duration_days=365,
        exam_code="sca",
        station_limit=2,
    )
    await a_customer(db_session, "org-grant@example.com")
    user = await identity_repo.user_by_email(db_session, "org-grant@example.com")
    assert user is not None
    await db_session.execute(
        update(User).where(User.email == "org-grant@example.com").values(exam_code="sca")
    )
    exam_row = await catalog_repo.exam_by_code(db_session, None, "sca")
    assert exam_row is not None
    await entitlements_repo.grant(
        db_session,
        user_id=user.id,
        exam_id=exam_row.id,
        source="org_grant",
        starts_at=FIXED_NOW - timedelta(days=1),
        ends_at=FIXED_NOW + timedelta(days=30),
    )
    await db_session.flush()
    token = mint_token(user_id=user.id, email="org-grant@example.com")

    rows = (await client.get("/api/v1/stations?exam_code=sca", headers=bearer(token))).json()["items"]

    assert len(rows) == 5


async def test_a_platform_admin_sees_the_too_old_station(
    client: AsyncClient,
    db_session: AsyncSession,
    make_actor,  # type: ignore[no-untyped-def]
) -> None:
    """Staff see the whole catalogue: the date floor hides nothing from a platform admin."""
    await _five_stations_and_one_too_old(db_session)
    token = await make_actor("floor-admin@osceguide.com", platform_admin=True)

    rows = (await client.get("/api/v1/stations?exam_code=sca", headers=bearer(token))).json()["items"]

    assert "Too old" in {row["title"] for row in rows}
