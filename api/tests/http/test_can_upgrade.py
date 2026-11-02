"""`service_station_limit.can_upgrade`: whether "Upgrade to Pro" is offered, which is only to
someone with no paid access for their exam, worked out through real checkouts (webhook
deliveries), the same way a customer's access is ever created.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.billing import repository as billing_repo
from app.features.billing import service_station_limit
from app.features.entitlements import repository as entitlements_repo
from app.features.identity import repository as identity_repo
from tests.http.test_billing_routes import a_customer, checkout_event, post_event
from tests.support.catalog import ensure_exam

pytestmark = pytest.mark.db

NOW = datetime(2026, 12, 1, tzinfo=UTC)


async def _buy(client: AsyncClient, email: str, *, event_id: str, price_id: str) -> None:
    """Walk one plan's checkout webhook through, exactly as Stripe would deliver it."""
    response = await post_event(client, checkout_event(event_id, email, price_id=price_id))
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "applied"


async def test_a_person_with_no_paid_access_can_always_upgrade(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Nothing yet to compare against, so the answer is always yes."""
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
    await a_customer(db_session, "no-access@example.com")
    user = await identity_repo.user_by_email(db_session, "no-access@example.com")
    assert user is not None

    result = await service_station_limit.can_upgrade(
        db_session, user_id=user.id, exam_id=exam.id, exam_code="sca", now=NOW
    )

    assert result is True


async def test_a_one_month_subscriber_is_not_offered_an_upgrade(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Holding the 1-month plan while a bigger one is on sale: still no button."""
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
    await a_customer(db_session, "smaller-plan@example.com")
    await _buy(client, "smaller-plan@example.com", event_id="evt_smaller", price_id="price_sca_1m")
    user = await identity_repo.user_by_email(db_session, "smaller-plan@example.com")
    assert user is not None

    result = await service_station_limit.can_upgrade(
        db_session, user_id=user.id, exam_id=exam.id, exam_code="sca", now=NOW
    )

    assert result is False


async def test_the_biggest_plan_holder_cannot_upgrade(client: AsyncClient, db_session: AsyncSession) -> None:
    """Holding the 6-month plan with no bigger plan on sale for the exam."""
    exam = await ensure_exam(db_session, "sca")
    await billing_repo.create_plan(
        db_session,
        code="sca_6m",
        stripe_price_id="price_sca_6m",
        amount_pence=5999,
        duration_days=180,
        exam_code="sca",
        station_limit=103,
    )
    await a_customer(db_session, "biggest-plan@example.com")
    await _buy(client, "biggest-plan@example.com", event_id="evt_biggest", price_id="price_sca_6m")
    user = await identity_repo.user_by_email(db_session, "biggest-plan@example.com")
    assert user is not None

    result = await service_station_limit.can_upgrade(
        db_session, user_id=user.id, exam_id=exam.id, exam_code="sca", now=NOW
    )

    assert result is False


async def test_a_plan_with_no_limit_cannot_be_upgraded_from(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Nothing is bigger than "everything": a NULL-limit plan already unlocks the whole library."""
    exam = await ensure_exam(db_session, "sca")
    await billing_repo.create_plan(
        db_session,
        code="sca_unlimited",
        stripe_price_id="price_sca_unlimited",
        amount_pence=9999,
        duration_days=365,
        exam_code="sca",
        station_limit=None,
    )
    await a_customer(db_session, "unlimited-plan@example.com")
    await _buy(client, "unlimited-plan@example.com", event_id="evt_unlimited", price_id="price_sca_unlimited")
    user = await identity_repo.user_by_email(db_session, "unlimited-plan@example.com")
    assert user is not None

    result = await service_station_limit.can_upgrade(
        db_session, user_id=user.id, exam_id=exam.id, exam_code="sca", now=NOW
    )

    assert result is False


async def test_an_org_grant_only_holder_cannot_upgrade(client: AsyncClient, db_session: AsyncSession) -> None:
    """An org grant counts as paid access, so the free-upgrade case does not apply; and since it
    carries no plan to read a limit from, `station_limit_for` answers "no limit", which already
    means they see everything."""
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
    await a_customer(db_session, "org-only@example.com")
    user = await identity_repo.user_by_email(db_session, "org-only@example.com")
    assert user is not None
    await entitlements_repo.grant(
        db_session,
        user_id=user.id,
        exam_id=exam.id,
        source="org_grant",
        starts_at=NOW - timedelta(days=1),
        ends_at=NOW + timedelta(days=30),
    )
    await db_session.flush()

    result = await service_station_limit.can_upgrade(
        db_session, user_id=user.id, exam_id=exam.id, exam_code="sca", now=NOW
    )

    assert result is False
