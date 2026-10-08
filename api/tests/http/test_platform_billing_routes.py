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
    kept = await post_event(client, checkout_event("evt_lost", "Typo@Example.com"))
    assert kept.json() == {"status": "needs_attention"}

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


# --------------------------------------------------------------------------
# The fixes
# --------------------------------------------------------------------------


async def test_a_refused_delivery_is_replayed_once_the_person_has_registered(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await a_plan(db_session)
    assert (await post_event(client, checkout_event("evt_late", "late@example.com"))).status_code == 200

    still = await client.post("/api/v1/platform/billing/events/evt_late/replay", headers=bearer(root))
    assert still.status_code == 200, still.text
    assert still.json() == {"status": "needs_attention"}, "nothing has changed, so still waiting"

    await a_customer(db_session, "late@example.com")
    replayed = await client.post("/api/v1/platform/billing/events/evt_late/replay", headers=bearer(root))
    assert replayed.status_code == 200, replayed.text
    assert replayed.json()["status"] == "applied"
    user = await identity_repo.user_by_email(db_session, "late@example.com")
    assert user is not None
    payments = await client.get(f"/api/v1/platform/users/{user.id}/payments", headers=bearer(root))
    assert len(payments.json()["items"]) == 1
    events = await client.get(f"/api/v1/platform/users/{user.id}/billing-events", headers=bearer(root))
    assert events.json()["items"][0]["processed_at"] is not None
    assert events.json()["items"][0]["failure"] is None

    again = await client.post("/api/v1/platform/billing/events/evt_late/replay", headers=bearer(root))
    assert again.json()["status"] == "already_applied"
    assert (
        len(
            (await client.get(f"/api/v1/platform/users/{user.id}/payments", headers=bearer(root))).json()[
                "items"
            ]
        )
        == 1
    )

    audit = await client.get("/api/v1/platform/audit?action=billing.event_replayed", headers=bearer(root))
    assert sorted(row["meta"]["outcome"] for row in audit.json()["items"]) == [
        "already_applied",
        "applied",
        "needs_attention",
    ], "the replay that found no account is on the record too"
    assert (
        await client.post("/api/v1/platform/billing/events/nope/replay", headers=bearer(root))
    ).status_code == 404


async def test_a_payment_that_did_not_come_through_stripe_grants_like_one_that_did(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await a_plan(db_session)
    await a_customer(db_session, "sponsored@example.com")
    user = await identity_repo.user_by_email(db_session, "sponsored@example.com")
    assert user is not None
    # Read once: a refused request below rolls the harness back and expires
    # the row, and reading it afterwards would be a synchronous lazy load.
    user_id = user.id

    recorded = await client.post(
        f"/api/v1/platform/users/{user_id}/payments",
        json={"plan_code": "one_month", "note": "bank transfer ref 4471"},
        headers=bearer(root),
    )
    assert recorded.status_code == 201, recorded.text
    body = recorded.json()
    assert body["plan_code"] == "one_month"
    assert body["amount_total_pence"] == 2499
    assert body["stripe_payment_intent_id"].startswith("manual:")
    assert body["receipt_id"]
    assert body["entitlement_id"]
    grants = await client.get(f"/api/v1/platform/users/{user_id}/entitlements", headers=bearer(root))
    assert [(g["source"], g["live"]) for g in grants.json()["items"]] == [("purchase", True)]

    explicit = {
        "plan_code": "one_month",
        "stripe_payment_intent_id": "pi_by_hand",
        "note": "x",
        "amount_total_pence": 0,
    }
    assert (
        await client.post(f"/api/v1/platform/users/{user_id}/payments", json=explicit, headers=bearer(root))
    ).status_code == 201
    duplicate = await client.post(
        f"/api/v1/platform/users/{user_id}/payments", json=explicit, headers=bearer(root)
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "payment_already_recorded"
    no_plan = await client.post(
        f"/api/v1/platform/users/{user_id}/payments",
        json={"plan_code": "lifetime", "note": "x"},
        headers=bearer(root),
    )
    assert no_plan.status_code == 404
    assert no_plan.json()["code"] == "plan_not_available"


async def test_a_refund_withdraws_the_access_and_keeps_the_sale(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await a_plan(db_session)
    await a_customer(db_session, "refunded@example.com")
    await post_event(client, checkout_event("evt_refund", "refunded@example.com"))
    user = await identity_repo.user_by_email(db_session, "refunded@example.com")
    assert user is not None
    [payment] = (await client.get(f"/api/v1/platform/users/{user.id}/payments", headers=bearer(root))).json()[
        "items"
    ]

    refunded = await client.post(
        f"/api/v1/platform/payments/{payment['id']}/refund",
        json={"reason": "changed their mind"},
        headers=bearer(root),
    )
    assert refunded.status_code == 200, refunded.text
    assert refunded.json()["entitlement_id"] == payment["entitlement_id"], (
        "the sale still says what it bought"
    )
    assert payment["access_revoked"] is False
    assert refunded.json()["access_revoked"] is True
    [grant] = (
        await client.get(f"/api/v1/platform/users/{user.id}/entitlements", headers=bearer(root))
    ).json()["items"]
    assert grant["live"] is False
    assert grant["revoked_at"] is not None
    assert (
        len(
            (await client.get(f"/api/v1/platform/users/{user.id}/payments", headers=bearer(root))).json()[
                "items"
            ]
        )
        == 1
    )

    twice = await client.post(
        f"/api/v1/platform/payments/{payment['id']}/refund", json={"reason": "again"}, headers=bearer(root)
    )
    assert twice.status_code == 200
    revocations = await client.get("/api/v1/platform/audit?action=entitlement.revoked", headers=bearer(root))
    assert len(revocations.json()["items"]) == 1
    refunds = await client.get("/api/v1/platform/audit?action=billing.refund_recorded", headers=bearer(root))
    assert len(refunds.json()["items"]) == 1, "a repeat withdraws nothing and writes no audit row"
    assert (
        await client.post(
            f"/api/v1/platform/payments/{uuid.uuid4()}/refund", json={"reason": "x"}, headers=bearer(root)
        )
    ).status_code == 404


async def test_a_console_refund_takes_back_the_referral_credit_like_the_webhook(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from tests.http.test_billing_routes import _bought_with_a_code

    root = await make_actor("root@osceguide.com", platform_admin=True)
    referrer_token, buyer, _, _ = await _bought_with_a_code(client, make_actor, db_session, "console")
    [payment] = (
        await client.get(f"/api/v1/platform/users/{buyer.id}/payments", headers=bearer(root))
    ).json()["items"]

    for _ in range(2):
        refunded = await client.post(
            f"/api/v1/platform/payments/{payment['id']}/refund", json={"reason": "x"}, headers=bearer(root)
        )
        assert refunded.status_code == 200

    mine = await client.get("/api/v1/me/referrals", headers=bearer(referrer_token))
    assert mine.json()["earned_pence"] == 0
