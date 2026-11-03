"""The support view of billing: what was paid, what was delivered, what was refused."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.billing import repository as billing_repo
from app.features.billing import service_platform_actions
from app.features.identity import repository as identity_repo
from tests.http.test_billing_routes import a_customer, checkout_event, post_event
from tests.support.billing import a_plan
from tests.support.fakes import FakeCheckoutSessions
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
    assert body["amount_total_pence"] == 0, "an omitted amount is a free grant"
    assert body["stripe_payment_intent_id"].startswith("manual:")
    assert body["receipt_id"]
    assert body["entitlement_id"]
    access = await client.get(f"/api/v1/platform/users/{user_id}/billing-access", headers=bearer(root))
    [exam_access] = access.json()["items"]
    assert [
        (g["source"], g["live"], g["plan_code"], g["payment_id"], g["payment_reference"])
        for g in exam_access["grants"]
    ] == [("purchase", True, "one_month", body["id"], body["stripe_payment_intent_id"])]

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
    [exam_access] = (
        await client.get(f"/api/v1/platform/users/{user.id}/billing-access", headers=bearer(root))
    ).json()["items"]
    [grant] = exam_access["grants"]
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


@pytest.fixture
def stripe(client: AsyncClient):  # type: ignore[no-untyped-def]
    """Stripe as the refund route sees it, without the internet."""
    fake = FakeCheckoutSessions()
    overrides = client._transport.app.dependency_overrides  # type: ignore[attr-defined]
    overrides[service_platform_actions.get_stripe_refunds] = lambda: fake
    yield fake
    overrides.pop(service_platform_actions.get_stripe_refunds, None)


async def _paid(client: AsyncClient, make_actor, db_session: AsyncSession, name: str):  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await a_plan(db_session)
    await a_customer(db_session, f"{name}@example.com")
    await post_event(client, checkout_event(f"evt_{name}", f"{name}@example.com"))
    user = await identity_repo.user_by_email(db_session, f"{name}@example.com")
    assert user is not None
    [payment] = (await client.get(f"/api/v1/platform/users/{user.id}/payments", headers=bearer(root))).json()[
        "items"
    ]
    return root, user, payment


async def test_a_stripe_refund_moves_the_money_then_withdraws_the_access(
    client: AsyncClient, make_actor, db_session: AsyncSession, stripe: FakeCheckoutSessions
) -> None:  # type: ignore[no-untyped-def]
    """P-28: Refund refunds in Stripe, keyed on payment and amount: a double click is one refund."""
    root, _, payment = await _paid(client, make_actor, db_session, "stripe-refund")
    url = f"/api/v1/platform/payments/{payment['id']}/stripe-refund"

    refunded = await client.post(url, json={"reason": "asked nicely"}, headers=bearer(root))
    assert refunded.status_code == 200, refunded.text
    assert refunded.json()["access_revoked"] is True
    assert stripe.refunds == [
        {
            "payment_intent_id": "pi_evt_stripe-refund",
            "amount_pence": 2499,
            "idempotency_key": f"refund:{payment['id']}:2499",
        }
    ]
    # Review of cc153db: a second click is refused before Stripe is asked again.
    again = await client.post(url, json={"reason": "again"}, headers=bearer(root))
    assert again.status_code == 409
    assert again.json()["code"] == "payment_already_refunded"
    assert len(stripe.refunds) == 1


async def test_a_stripe_refund_after_a_recorded_refund_never_reaches_stripe(
    client: AsyncClient, make_actor, db_session: AsyncSession, stripe: FakeCheckoutSessions
) -> None:  # type: ignore[no-untyped-def]
    root, _, payment = await _paid(client, make_actor, db_session, "recorded-first")
    recorded = await client.post(
        f"/api/v1/platform/payments/{payment['id']}/refund", json={"reason": "by hand"}, headers=bearer(root)
    )
    assert recorded.status_code == 200, recorded.text

    refused = await client.post(
        f"/api/v1/platform/payments/{payment['id']}/stripe-refund",
        json={"reason": "again"},
        headers=bearer(root),
    )

    assert refused.status_code == 409
    assert refused.json()["code"] == "payment_already_refunded"
    assert stripe.refunds == []


async def test_a_stripe_refund_on_a_disputed_payment_never_reaches_stripe(
    client: AsyncClient, make_actor, db_session: AsyncSession, stripe: FakeCheckoutSessions
) -> None:  # type: ignore[no-untyped-def]
    root, _, payment = await _paid(client, make_actor, db_session, "disputed-first")
    intent = "pi_evt_disputed-first"
    await post_event(
        client,
        {
            "id": "evt_disp_sr",
            "type": "charge.dispute.created",
            "data": {"object": {"payment_intent": intent}},
        },
    )

    refused = await client.post(
        f"/api/v1/platform/payments/{payment['id']}/stripe-refund",
        json={"reason": "x"},
        headers=bearer(root),
    )

    assert refused.status_code == 409
    assert refused.json()["code"] == "payment_already_refunded"
    assert stripe.refunds == []


async def test_stripe_refusing_a_refund_is_a_conflict_with_its_reason_not_an_outage(
    client: AsyncClient, make_actor, db_session: AsyncSession, stripe: FakeCheckoutSessions
) -> None:  # type: ignore[no-untyped-def]
    root, _, payment = await _paid(client, make_actor, db_session, "stripe-says-no")
    stripe.refusal = "Charge ch_1 has already been refunded."

    refused = await client.post(
        f"/api/v1/platform/payments/{payment['id']}/stripe-refund", json={"reason": "x"}, headers=bearer(root)
    )

    assert refused.status_code == 409
    assert refused.json()["code"] == "stripe_refund_refused"
    assert "already been refunded" in refused.json()["message"]
    after = await client.get(f"/api/v1/platform/users/{payment['user_id']}/payments", headers=bearer(root))
    assert after.json()["items"][0]["access_revoked"] is False


async def test_a_stripe_refusal_leaves_the_access_alone(
    client: AsyncClient, make_actor, db_session: AsyncSession, stripe: FakeCheckoutSessions
) -> None:  # type: ignore[no-untyped-def]
    root, _, payment = await _paid(client, make_actor, db_session, "stripe-down")
    stripe.fails = True

    refused = await client.post(
        f"/api/v1/platform/payments/{payment['id']}/stripe-refund", json={"reason": "x"}, headers=bearer(root)
    )

    assert refused.status_code == 503
    assert refused.json()["code"] == "stripe_refund_failed"
    after = await client.get(f"/api/v1/platform/users/{payment['user_id']}/payments", headers=bearer(root))
    assert after.json()["items"][0]["access_revoked"] is False


async def test_a_payment_that_never_went_through_stripe_cannot_be_refunded_there(
    client: AsyncClient, make_actor, db_session: AsyncSession, stripe: FakeCheckoutSessions
) -> None:  # type: ignore[no-untyped-def]
    root, user, _ = await _paid(client, make_actor, db_session, "manual")
    made = await client.post(
        f"/api/v1/platform/users/{user.id}/payments",
        json={"plan_code": "one_month", "note": "invoice paid by bank transfer"},
        headers=bearer(root),
    )
    assert made.status_code == 201, made.text

    refused = await client.post(
        f"/api/v1/platform/payments/{made.json()['id']}/stripe-refund",
        json={"reason": "x"},
        headers=bearer(root),
    )

    assert refused.status_code == 409
    assert refused.json()["code"] == "not_a_stripe_payment"
    assert stripe.refunds == []


async def test_an_event_recorded_but_never_processed_is_in_the_queue_and_can_be_retried(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await billing_repo.record_event(
        db_session, event_id="evt_stuck", event_type="customer.created", event_payload={"id": "evt_stuck"}
    )
    await db_session.commit()

    queue = await client.get("/api/v1/platform/billing/events?failed_only=true", headers=bearer(root))
    assert [e["event_id"] for e in queue.json()["items"]] == ["evt_stuck"]

    retried = await client.post("/api/v1/platform/billing/events/evt_stuck/replay", headers=bearer(root))
    assert retried.status_code == 200, retried.text
    queue = await client.get("/api/v1/platform/billing/events?failed_only=true", headers=bearer(root))
    assert queue.json()["items"] == []


async def test_a_webhook_delivery_locks_its_ledger_row_before_checking_it_was_applied(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Review of cc153db: two deliveries of one event queue on the row, so the loser sees it applied."""
    from sqlalchemy import event

    from app.features.billing import service as billing_service

    statements: list[str] = []

    def record(conn, cursor, statement, *args):  # type: ignore[no-untyped-def]
        statements.append(statement)

    await a_plan(db_session)
    await a_customer(db_session, "lock@example.com")
    delivery = checkout_event("evt_lock", "lock@example.com")
    # Recorded by a delivery that has not been applied (or is being applied right now).
    await billing_repo.record_event(
        db_session, event_id="evt_lock", event_type=delivery["type"], event_payload=delivery
    )
    sync_engine = db_session.bind.sync_engine  # type: ignore[union-attr]
    event.listen(sync_engine, "before_cursor_execute", record)
    try:
        await billing_service.handle_event(db_session, event=delivery, now=datetime.now(UTC))
    finally:
        event.remove(sync_engine, "before_cursor_execute", record)

    assert [s for s in statements if "FROM stripe_events" in s and "FOR UPDATE" in s], statements


async def _manual_payment(client, root, user_id, **extra):  # type: ignore[no-untyped-def]
    """Record one manual payment for the plan `one_month` and return the response."""
    return await client.post(
        f"/api/v1/platform/users/{user_id}/payments",
        json={"plan_code": "one_month", "note": "test", **extra},
        headers=bearer(root),
    )


async def _receipt_count(db_session: AsyncSession) -> int:
    """How many payment receipt emails are queued on the outbox."""
    from sqlalchemy import func, select

    from app.features.notifications.models import OutboundMessage

    return int(
        await db_session.scalar(
            select(func.count())
            .select_from(OutboundMessage)
            .where(OutboundMessage.template_key == "payment_receipt")
        )
        or 0
    )


async def test_a_free_manual_payment_is_a_capped_purchase_and_the_receipt_is_opt_in(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from sqlalchemy import text

    from app.features.billing import service_station_limit
    from app.features.catalog import service as catalog

    root = await make_actor("root@osceguide.com", platform_admin=True)
    await a_plan(db_session)
    await db_session.execute(text("update plans set station_limit = 53 where code = 'one_month'"))
    await a_customer(db_session, "free@example.com")
    user = await identity_repo.user_by_email(db_session, "free@example.com")
    assert user is not None
    user_id = user.id
    exam = await catalog.resolve_exam(db_session, "sca", org_id=None)
    exam_id = exam.id

    silent = await _manual_payment(client, root, user_id)
    assert silent.status_code == 201, silent.text
    assert silent.json()["amount_total_pence"] == 0
    assert silent.json()["plan_starts_at"] and silent.json()["plan_ends_at"]
    assert await _receipt_count(db_session) == 0
    limit = await service_station_limit.station_limit_for(
        db_session, user_id=user_id, exam_id=exam_id, exam_code="sca", now=datetime.now(UTC)
    )
    assert limit == 53

    loud = await _manual_payment(client, root, user_id, send_receipt=True)
    assert loud.status_code == 201, loud.text
    assert await _receipt_count(db_session) == 1


async def test_start_now_runs_alongside_and_after_current_queues_behind(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await a_plan(db_session)
    await a_customer(db_session, "stack@example.com")
    user = await identity_repo.user_by_email(db_session, "stack@example.com")
    assert user is not None
    user_id = user.id
    paid_at = datetime.now(UTC)

    first = (await _manual_payment(client, root, user_id)).json()
    queued = (await _manual_payment(client, root, user_id)).json()
    assert queued["plan_starts_at"] == first["plan_ends_at"], "after_current waits for the running plan"
    alongside = (await _manual_payment(client, root, user_id, start="now")).json()
    assert alongside["plan_starts_at"] < first["plan_ends_at"], "now overlaps the running plan"
    assert datetime.fromisoformat(alongside["plan_starts_at"]) >= paid_at.replace(microsecond=0)


async def test_the_billing_read_gives_the_limit_and_why(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from app.features.billing import repository as billing_repository
    from app.features.entitlements import repository as ent_repository
    from tests.support.catalog import ensure_exam

    root = await make_actor("root@osceguide.com", platform_admin=True)
    await a_plan(db_session)
    await billing_repository.create_plan(
        db_session,
        code="sca_1m",
        stripe_price_id="price_sca_1m",
        amount_pence=2499,
        duration_days=30,
        exam_code="sca",
        station_limit=53,
    )
    await a_customer(db_session, "reader@example.com")
    user = await identity_repo.user_by_email(db_session, "reader@example.com")
    assert user is not None
    user_id = user.id
    exam = await ensure_exam(db_session, "sca")
    exam_id = exam.id

    bought = await client.post(
        f"/api/v1/platform/users/{user_id}/payments",
        json={"plan_code": "sca_1m", "note": "x"},
        headers=bearer(root),
    )
    assert bought.status_code == 201, bought.text
    capped = await client.get(f"/api/v1/platform/users/{user_id}/billing-access", headers=bearer(root))
    [row] = capped.json()["items"]
    assert (row["exam_code"], row["station_limit"], row["stations_sat"]) == ("sca", 53, 0)
    assert row["limit_reason"] == "plan:sca_1m"
    assert row["grants"][0]["plan_code"] == "sca_1m"

    await ent_repository.grant(db_session, user_id=user_id, exam_id=exam_id, source="org_grant")
    await db_session.flush()
    overlapped = await client.get(f"/api/v1/platform/users/{user_id}/billing-access", headers=bearer(root))
    [row] = overlapped.json()["items"]
    assert row["station_limit"] is None
    assert row["limit_reason"] == "unlimited:org_grant"
