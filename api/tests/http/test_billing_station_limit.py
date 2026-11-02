"""`service_station_limit.station_limit_for`: what a person's live purchases unlock, worked out
through real checkouts (webhook deliveries), the same way a customer's access is ever created.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.billing import repository as billing_repo
from app.features.billing import service_station_limit
from app.features.catalog import repository as catalog_repo
from app.features.entitlements import repository as entitlements_repo
from app.features.identity import repository as identity_repo
from tests.http.test_billing_routes import a_customer, checkout_event, post_event
from tests.support.catalog import ensure_exam

pytestmark = pytest.mark.db

NOW = datetime(2026, 11, 1, tzinfo=UTC)


async def _buy(client: AsyncClient, email: str, *, event_id: str, price_id: str) -> None:
    """Walk one plan's checkout webhook through, exactly as Stripe would deliver it."""
    response = await post_event(client, checkout_event(event_id, email, price_id=price_id))
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "applied"


async def test_one_live_plan_returns_its_own_limit(client: AsyncClient, db_session: AsyncSession) -> None:
    """A single live purchase with a limit of 53 returns 53."""
    exam = await ensure_exam(db_session, "sca")
    await billing_repo.create_plan(
        db_session,
        code="sca_1m",
        stripe_price_id="price_sca_1m",
        amount_pence=2499,
        duration_days=30,
        exam_code="sca",
        station_limit=53,
    )
    await a_customer(db_session, "one-plan@example.com")
    await _buy(client, "one-plan@example.com", event_id="evt_one", price_id="price_sca_1m")
    user = await identity_repo.user_by_email(db_session, "one-plan@example.com")
    assert user is not None

    limit = await service_station_limit.station_limit_for(
        db_session, user_id=user.id, exam_id=exam.id, exam_code="sca", now=NOW
    )

    assert limit == 53


async def test_two_live_plans_return_the_larger_limit(client: AsyncClient, db_session: AsyncSession) -> None:
    """Holding both the 1-month (53) and 3-month (78) plan returns the larger, 78."""
    exam = await ensure_exam(db_session, "sca")
    await billing_repo.create_plan(
        db_session,
        code="sca_1m",
        stripe_price_id="price_sca_1m",
        amount_pence=2499,
        duration_days=30,
        exam_code="sca",
        station_limit=53,
    )
    await billing_repo.create_plan(
        db_session,
        code="sca_3m",
        stripe_price_id="price_sca_3m",
        amount_pence=3999,
        duration_days=90,
        exam_code="sca",
        station_limit=78,
    )
    await a_customer(db_session, "two-plans@example.com")
    await _buy(client, "two-plans@example.com", event_id="evt_two_a", price_id="price_sca_1m")
    await _buy(client, "two-plans@example.com", event_id="evt_two_b", price_id="price_sca_3m")
    user = await identity_repo.user_by_email(db_session, "two-plans@example.com")
    assert user is not None

    limit = await service_station_limit.station_limit_for(
        db_session, user_id=user.id, exam_id=exam.id, exam_code="sca", now=NOW
    )

    assert limit == 78


async def test_a_plan_with_no_limit_wins_over_a_smaller_one(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Any live plan with a NULL `station_limit` makes the whole result None, even alongside a
    numbered one."""
    exam = await ensure_exam(db_session, "sca")
    await billing_repo.create_plan(
        db_session,
        code="sca_1m",
        stripe_price_id="price_sca_1m",
        amount_pence=2499,
        duration_days=30,
        exam_code="sca",
        station_limit=53,
    )
    await billing_repo.create_plan(
        db_session,
        code="sca_6m",
        stripe_price_id="price_sca_6m",
        amount_pence=7999,
        duration_days=180,
        exam_code="sca",
        station_limit=None,
    )
    await a_customer(db_session, "unlimited@example.com")
    await _buy(client, "unlimited@example.com", event_id="evt_unlimited_a", price_id="price_sca_1m")
    await _buy(client, "unlimited@example.com", event_id="evt_unlimited_b", price_id="price_sca_6m")
    user = await identity_repo.user_by_email(db_session, "unlimited@example.com")
    assert user is not None

    limit = await service_station_limit.station_limit_for(
        db_session, user_id=user.id, exam_id=exam.id, exam_code="sca", now=NOW
    )

    assert limit is None


async def test_a_referral_plan_uses_its_base_plans_limit(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Buying through the referral twin still reads the base plan's `station_limit`."""
    exam = await ensure_exam(db_session, "sca")
    await billing_repo.create_plan(
        db_session,
        code="sca_1m",
        stripe_price_id="price_sca_1m",
        amount_pence=2499,
        duration_days=30,
        exam_code="sca",
        station_limit=53,
    )
    await billing_repo.create_plan(
        db_session,
        code="sca_1m_referral",
        stripe_price_id="price_sca_1m_referral",
        amount_pence=2249,
        duration_days=30,
        exam_code="sca",
        station_limit=53,
    )
    await a_customer(db_session, "referral@example.com")
    await _buy(client, "referral@example.com", event_id="evt_referral", price_id="price_sca_1m_referral")
    user = await identity_repo.user_by_email(db_session, "referral@example.com")
    assert user is not None

    limit = await service_station_limit.station_limit_for(
        db_session, user_id=user.id, exam_id=exam.id, exam_code="sca", now=NOW
    )

    assert limit == 53


async def test_an_expired_purchase_returns_no_limit(client: AsyncClient, db_session: AsyncSession) -> None:
    """A purchase that has already lapsed is not a live grant, so there is nothing to cap."""
    exam = await ensure_exam(db_session, "sca")
    await billing_repo.create_plan(
        db_session,
        code="sca_1m",
        stripe_price_id="price_sca_1m",
        amount_pence=2499,
        duration_days=30,
        exam_code="sca",
        station_limit=53,
    )
    await a_customer(db_session, "lapsed@example.com")
    await _buy(client, "lapsed@example.com", event_id="evt_lapsed", price_id="price_sca_1m")
    user = await identity_repo.user_by_email(db_session, "lapsed@example.com")
    assert user is not None
    far_future = NOW + timedelta(days=400)

    limit = await service_station_limit.station_limit_for(
        db_session, user_id=user.id, exam_id=exam.id, exam_code="sca", now=far_future
    )

    assert limit is None


async def test_a_live_purchase_alongside_a_live_org_grant_returns_no_limit(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """An org grant running at the same time as a purchase is not read: the org grant may
    already cover the whole library, which this slice cannot tell from here."""
    exam = await ensure_exam(db_session, "sca")
    await billing_repo.create_plan(
        db_session,
        code="sca_1m",
        stripe_price_id="price_sca_1m",
        amount_pence=2499,
        duration_days=30,
        exam_code="sca",
        station_limit=53,
    )
    await a_customer(db_session, "both@example.com")
    await _buy(client, "both@example.com", event_id="evt_both", price_id="price_sca_1m")
    user = await identity_repo.user_by_email(db_session, "both@example.com")
    assert user is not None
    exam_row = await catalog_repo.exam_by_code(db_session, None, "sca")
    assert exam_row is not None
    await entitlements_repo.grant(
        db_session,
        user_id=user.id,
        exam_id=exam_row.id,
        source="org_grant",
        starts_at=NOW - timedelta(days=1),
        ends_at=NOW + timedelta(days=30),
    )

    limit = await service_station_limit.station_limit_for(
        db_session, user_id=user.id, exam_id=exam.id, exam_code="sca", now=NOW
    )

    assert limit is None
