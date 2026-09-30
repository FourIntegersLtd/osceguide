"""Staff pricing: a plan is created with its Stripe prices and referral twin, and retired without
refusing a payment already under way."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.billing import repository as billing_repo
from app.features.billing import service_plans
from tests.http.test_billing_routes import a_customer, checkout_event, post_event
from tests.support.catalog import ensure_exam
from tests.support.fakes import FakeCheckoutSessions
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

PLANS = "/api/v1/platform/billing/plans"
NEW_PLAN = {"exam_code": "sca", "code": "sca_2m", "amount_pence": 3999, "duration_days": 60}


@pytest.fixture
def stripe(client: AsyncClient) -> Iterator[FakeCheckoutSessions]:
    """Stripe as the price routes see it, without the internet."""
    fake = FakeCheckoutSessions()
    overrides = client._transport.app.dependency_overrides  # type: ignore[attr-defined]
    overrides[service_plans.get_stripe_prices] = lambda: fake
    yield fake
    overrides.pop(service_plans.get_stripe_prices, None)


async def test_staff_price_an_exam_and_customers_can_buy_it(
    client: AsyncClient, make_actor, db_session: AsyncSession, stripe: FakeCheckoutSessions
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await ensure_exam(db_session, "sca")

    created = await client.post(PLANS, json=NEW_PLAN, headers=bearer(root))

    assert created.status_code == 201, created.text
    body = created.json()
    assert body["code"] == "sca_2m"
    assert body["amount_pence"] == 3999
    assert body["referral_amount_pence"] == 3599
    assert body["active"] is True
    assert body["stripe_price_id"] == "price_fake_sca_2m"
    assert [(price["plan_code"], price["amount_pence"]) for price in stripe.prices] == [
        ("sca_2m", 3999),
        ("sca_2m_referral", 3599),
    ]
    public = await client.get("/api/v1/billing/plans")
    [listed] = public.json()["items"]
    assert (listed["code"], listed["referral_amount_pence"]) == ("sca_2m", 3599)


async def test_a_retired_plan_is_off_sale_but_a_payment_under_way_still_grants(
    client: AsyncClient, make_actor, db_session: AsyncSession, stripe: FakeCheckoutSessions
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await ensure_exam(db_session, "sca")
    assert (await client.post(PLANS, json=NEW_PLAN, headers=bearer(root))).status_code == 201

    retired = await client.patch(f"{PLANS}/sca_2m", json={"active": False}, headers=bearer(root))

    assert retired.status_code == 200, retired.text
    assert retired.json()["active"] is False
    twin = await billing_repo.any_plan_by_code(db_session, "sca_2m_referral")
    assert twin is not None and twin.active is False
    assert (await client.get("/api/v1/billing/plans")).json()["items"] == []
    staff_view = (await client.get(PLANS, headers=bearer(root))).json()["items"]
    assert [(plan["code"], plan["active"]) for plan in staff_view] == [("sca_2m", False)]
    await a_customer(db_session, "late@example.com")
    paid = await post_event(
        client, checkout_event("evt_late", "late@example.com", price_id="price_fake_sca_2m")
    )
    assert paid.status_code == 200, paid.text
    assert paid.json()["status"] == "applied"


async def test_a_plan_code_is_never_reused(
    client: AsyncClient, make_actor, db_session: AsyncSession, stripe: FakeCheckoutSessions
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await ensure_exam(db_session, "sca")
    assert (await client.post(PLANS, json=NEW_PLAN, headers=bearer(root))).status_code == 201

    again = await client.post(PLANS, json=NEW_PLAN, headers=bearer(root))
    twin_named = await client.post(PLANS, json={**NEW_PLAN, "code": "sca_1m_referral"}, headers=bearer(root))

    assert again.status_code == 409
    assert again.json()["code"] == "plan_code_taken"
    assert twin_named.json()["code"] == "plan_code_taken"
    assert len(stripe.prices) == 2


async def test_only_a_published_platform_exam_is_priced(
    client: AsyncClient, make_actor, db_session: AsyncSession, stripe: FakeCheckoutSessions
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await ensure_exam(db_session, "draftexam", published=False)

    draft = await client.post(PLANS, json={**NEW_PLAN, "exam_code": "draftexam"}, headers=bearer(root))
    missing = await client.post(PLANS, json={**NEW_PLAN, "exam_code": "nope"}, headers=bearer(root))

    assert (draft.status_code, draft.json()["code"]) == (404, "unknown_exam")
    assert missing.json()["code"] == "unknown_exam"
    assert stripe.prices == []


async def test_stripe_refusing_writes_no_plan(
    client: AsyncClient, make_actor, db_session: AsyncSession, stripe: FakeCheckoutSessions
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await ensure_exam(db_session, "sca")
    stripe.fails = True

    refused = await client.post(PLANS, json=NEW_PLAN, headers=bearer(root))

    assert (refused.status_code, refused.json()["code"]) == (503, "price_creation_failed")
    assert await billing_repo.any_plan_by_code(db_session, "sca_2m") is None


async def test_a_referral_twin_is_managed_through_its_plan_and_only_staff_price(
    client: AsyncClient, make_actor, db_session: AsyncSession, stripe: FakeCheckoutSessions
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    customer = await make_actor("someone@example.com")
    await ensure_exam(db_session, "sca")
    assert (await client.post(PLANS, json=NEW_PLAN, headers=bearer(root))).status_code == 201

    twin = await client.patch(f"{PLANS}/sca_2m_referral", json={"active": False}, headers=bearer(root))
    outsider = await client.post(PLANS, json={**NEW_PLAN, "code": "sca_3m"}, headers=bearer(customer))

    assert (twin.status_code, twin.json()["code"]) == (404, "plan_not_found")
    assert outsider.status_code == 403


async def test_a_plan_goes_back_on_sale_only_while_its_exam_can_be_granted(
    client: AsyncClient, make_actor, db_session: AsyncSession, stripe: FakeCheckoutSessions
) -> None:  # type: ignore[no-untyped-def]
    """A legacy row with no exam would charge a card and grant nothing, so it stays off sale."""
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await ensure_exam(db_session, "sca")
    await billing_repo.create_plan(
        db_session,
        code="legacy_1m",
        stripe_price_id="price_legacy",
        amount_pence=2499,
        duration_days=30,
        exam_code="",
    )
    await billing_repo.set_plans_active(db_session, ["legacy_1m"], active=False)
    assert (await client.post(PLANS, json=NEW_PLAN, headers=bearer(root))).status_code == 201
    assert (
        await client.patch(f"{PLANS}/sca_2m", json={"active": False}, headers=bearer(root))
    ).status_code == 200

    back = await client.patch(f"{PLANS}/sca_2m", json={"active": True}, headers=bearer(root))
    assert back.status_code == 200, back.text
    assert back.json()["active"] is True
    assert [plan["code"] for plan in (await client.get("/api/v1/billing/plans")).json()["items"]] == [
        "sca_2m"
    ]

    legacy = await client.patch(f"{PLANS}/legacy_1m", json={"active": True}, headers=bearer(root))
    missing = await client.patch(f"{PLANS}/nope_1m", json={"active": True}, headers=bearer(root))
    assert (legacy.status_code, legacy.json()["code"]) == (404, "unknown_exam")
    assert missing.json()["code"] == "plan_not_found"
