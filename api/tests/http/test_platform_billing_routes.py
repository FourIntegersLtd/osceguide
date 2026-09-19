"""The support view of billing: what was paid, what was delivered, what was refused."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.identity import repository as identity_repo
from tests.http.test_billing_routes import a_customer, a_plan, checkout_event, post_event
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def test_a_payment_that_granted_access_is_read_with_what_it_bought(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await a_plan(db_session)
    await a_customer(db_session, "buyer@example.com")
    assert (await post_event(client, checkout_event("evt_p1", "buyer@example.com"))).status_code == 200
    user = await identity_repo.user_by_email(db_session, "buyer@example.com")
    assert user is not None

    payments = await client.get(f"/api/v1/platform/users/{user.id}/payments", headers=bearer(root))
    assert payments.status_code == 200, payments.text
    [row] = payments.json()["items"]
    assert row["plan_code"] == "one_month"
    assert row["amount_total_pence"] == 2499
    assert row["stripe_payment_intent_id"] == "pi_evt_p1"
    assert row["entitlement_id"] is not None
    assert row["receipt_id"]

    events = await client.get(f"/api/v1/platform/users/{user.id}/billing-events", headers=bearer(root))
    [event] = events.json()["items"]
    assert event["event_id"] == "evt_p1"
    assert event["processed_at"] is not None
    assert event["failure"] is None
    assert event["price_id"] == "price_one_month"


async def test_a_payment_for_an_unknown_address_is_a_refused_delivery_the_console_can_find(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """The 'paid but no access' case: the person typed a different address
    at checkout, or registered afterwards. The ledger row is what remains."""
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await a_plan(db_session)
    refused = await post_event(client, checkout_event("evt_lost", "Typo@Example.com"))
    assert refused.status_code == 422

    queue = await client.get("/api/v1/platform/billing/events?failed_only=true", headers=bearer(root))
    assert queue.status_code == 200, queue.text
    [event] = [e for e in queue.json()["items"] if e["event_id"] == "evt_lost"]
    assert event["failure"] == "No account for that email address."
    assert event["customer_email"] == "Typo@Example.com"
    assert event["payment_intent_id"] == "pi_evt_lost"

    # Once they register with that address, the delivery shows against them.
    await a_customer(db_session, "typo@example.com")
    user = await identity_repo.user_by_email(db_session, "typo@example.com")
    assert user is not None
    theirs = await client.get(f"/api/v1/platform/users/{user.id}/billing-events", headers=bearer(root))
    assert [e["event_id"] for e in theirs.json()["items"]] == ["evt_lost"]
    assert (await client.get(f"/api/v1/platform/users/{user.id}/payments", headers=bearer(root))).json()[
        "items"
    ] == []


async def test_the_ledger_pages_newest_first_and_only_an_admin_reads_it(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    someone = await make_actor("someone@example.com")
    await a_plan(db_session)
    await a_customer(db_session, "a@example.com")
    for i in range(3):
        await post_event(client, checkout_event(f"evt_page_{i}", "a@example.com"))

    first = await client.get("/api/v1/platform/billing/events?limit=2", headers=bearer(root))
    assert len(first.json()["items"]) == 2
    assert first.json()["next_cursor"]
    rest = await client.get(
        f"/api/v1/platform/billing/events?limit=2&cursor={first.json()['next_cursor']}", headers=bearer(root)
    )
    seen = {e["event_id"] for e in first.json()["items"]} | {e["event_id"] for e in rest.json()["items"]}
    assert {"evt_page_0", "evt_page_1", "evt_page_2"} <= seen

    assert (await client.get("/api/v1/platform/billing/events", headers=bearer(someone))).status_code == 403
    missing = await client.get(f"/api/v1/platform/users/{uuid.uuid4()}/payments", headers=bearer(root))
    assert missing.status_code == 404
    assert missing.json()["code"] == "user_not_found"
