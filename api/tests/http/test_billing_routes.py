"""Applying a Stripe delivery, once."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.billing import repository as billing_repo
from app.features.identity import repository as identity_repo
from tests.support.catalog import ensure_exam
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


def signed_headers(payload: bytes) -> dict[str, str]:
    """Sign a body the way Stripe does, so the route sees a genuine request."""
    import hashlib
    import hmac
    import time

    from app.core.settings import get_settings

    secret = get_settings().stripe_webhook_secret
    timestamp = int(time.time())
    mac = hmac.new(secret.encode(), f"{timestamp}.".encode() + payload, hashlib.sha256).hexdigest()
    return {"Stripe-Signature": f"t={timestamp},v1={mac}", "Content-Type": "application/json"}


async def post_event(client: AsyncClient, event: dict):  # type: ignore[no-untyped-def]
    """Send a webhook as Stripe would: raw bytes, signed."""
    import json

    body = json.dumps(event).encode()
    return await client.post("/api/v1/billing/webhooks/stripe", content=body, headers=signed_headers(body))


def checkout_event(event_id: str, email: str, price_id: str = "price_one_month") -> dict:
    """Shaped as a real `checkout.session.completed` delivery: the price lives in
    the session's metadata (set when checkout was created), never at the top."""
    return {
        "id": event_id,
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_1",
                "object": "checkout.session",
                "customer_email": email,
                "metadata": {"price_id": price_id},
                "payment_intent": f"pi_{event_id}",
                "amount_total": 2499,
                "currency": "gbp",
            }
        },
    }


async def a_plan(db_session: AsyncSession) -> None:
    # A plan names an exam by code rather than by key, so the plan can be
    # written before the exam is — but granting the purchase resolves it, and
    # nothing is seeded.
    await ensure_exam(db_session, "sca")
    await billing_repo.create_plan(
        db_session,
        code="one_month",
        stripe_price_id="price_one_month",
        amount_pence=2499,
        duration_days=30,
        exam_code="sca",
    )
    await db_session.flush()


async def a_customer(db_session: AsyncSession, email: str) -> None:
    await identity_repo.create_user(session=db_session, email=email, name="C", password_hash=None)
    await db_session.flush()


async def test_plans_are_public(client: AsyncClient, db_session: AsyncSession) -> None:
    await a_plan(db_session)
    response = await client.get("/api/v1/billing/plans")
    assert response.status_code == 200
    assert response.json()["items"][0]["code"] == "one_month"


async def test_a_completed_checkout_grants_access(client: AsyncClient, db_session: AsyncSession) -> None:
    await a_plan(db_session)
    await a_customer(db_session, "buyer@example.com")
    response = await post_event(client, checkout_event("evt_1", "buyer@example.com"))
    assert response.status_code == 200
    assert response.json()["status"] == "applied"

    from app.features.entitlements import repository as ent_repo

    user = await identity_repo.user_by_email(db_session, "buyer@example.com")
    assert user is not None
    grants = await ent_repo.for_user(db_session, user.id)
    assert [g.source for g in grants] == ["purchase"]
    assert grants[0].ends_at is not None


async def test_the_same_delivery_twice_grants_once(client: AsyncClient, db_session: AsyncSession) -> None:
    """Stripe retries until it gets a 2xx. b2c returns 500 on failure to force
    exactly that, with no record of what it already applied."""
    await a_plan(db_session)
    await a_customer(db_session, "retry@example.com")
    event = checkout_event("evt_2", "retry@example.com")

    first = await post_event(client, event)
    second = await post_event(client, event)
    assert first.json()["status"] == "applied"
    assert second.json()["status"] == "already_applied"

    from app.features.entitlements import repository as ent_repo

    user = await identity_repo.user_by_email(db_session, "retry@example.com")
    assert user is not None
    assert len(await ent_repo.for_user(db_session, user.id)) == 1


async def test_an_event_we_do_not_act_on_is_acknowledged(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Answering non-2xx would ask Stripe to keep delivering it forever."""
    response = await post_event(
        client, {"id": "evt_3", "type": "payment_intent.succeeded", "data": {"object": {}}}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"


async def test_an_unknown_price_fails_loudly_rather_than_guessing(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """The card has already been charged, so a guessed duration is worse than
    an error somebody has to look at."""
    await a_plan(db_session)
    await a_customer(db_session, "odd@example.com")
    response = await post_event(client, checkout_event("evt_4", "odd@example.com", price_id="price_unseen"))
    assert response.status_code == 404
    assert response.json()["code"] == "unknown_plan"


async def test_an_event_without_an_id_is_refused(client: AsyncClient) -> None:
    response = await post_event(client, {"type": "checkout.session.completed"})
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_webhook"


async def test_a_payment_record_links_to_what_it_bought(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await a_plan(db_session)
    await a_customer(db_session, "linked@example.com")
    await post_event(client, checkout_event("evt_5", "linked@example.com"))
    user = await identity_repo.user_by_email(db_session, "linked@example.com")
    assert user is not None
    payments = await billing_repo.payments_for_user(db_session, user.id)
    assert len(payments) == 1
    assert payments[0].entitlement_id is not None


async def test_an_unsigned_webhook_is_refused(client: AsyncClient) -> None:
    """The launch blocker. Without this the route trusts whatever it is sent."""
    import json

    body = json.dumps(checkout_event("evt_forged", "attacker@example.com")).encode()
    response = await client.post("/api/v1/billing/webhooks/stripe", content=body)
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_signature"


async def test_a_webhook_signed_with_the_wrong_secret_is_refused(client: AsyncClient) -> None:
    import hashlib
    import hmac
    import json
    import time

    body = json.dumps(checkout_event("evt_wrong", "attacker@example.com")).encode()
    timestamp = int(time.time())
    mac = hmac.new(b"whsec_not_ours", f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()
    response = await client.post(
        "/api/v1/billing/webhooks/stripe",
        content=body,
        headers={"Stripe-Signature": f"t={timestamp},v1={mac}"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_signature"


async def test_a_tampered_body_is_refused(client: AsyncClient, db_session: AsyncSession) -> None:
    """Sign one body, send another. This is what the signature is for."""
    import json

    await a_plan(db_session)
    await a_customer(db_session, "tamper@example.com")
    honest = json.dumps(checkout_event("evt_tamper", "tamper@example.com")).encode()
    headers = signed_headers(honest)

    tampered = json.dumps(checkout_event("evt_tamper", "attacker@example.com")).encode()
    response = await client.post("/api/v1/billing/webhooks/stripe", content=tampered, headers=headers)
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_signature"


async def test_the_price_is_read_from_expanded_line_items_too(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """A checkout created without metadata still names its price in the line items."""
    await a_plan(db_session)
    await a_customer(db_session, "items@example.com")
    event = checkout_event("evt_items", "items@example.com")
    del event["data"]["object"]["metadata"]
    event["data"]["object"]["line_items"] = {"data": [{"price": {"id": "price_one_month"}}]}
    response = await post_event(client, event)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "applied"


async def test_a_top_level_price_id_is_not_a_stripe_shape(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """The field the old handler read. No real delivery carries it."""
    await a_plan(db_session)
    await a_customer(db_session, "flat@example.com")
    event = checkout_event("evt_flat", "flat@example.com")
    event["data"]["object"] = {**event["data"]["object"], "price_id": "price_one_month"}
    del event["data"]["object"]["metadata"]
    response = await post_event(client, event)
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_webhook"


async def test_a_payment_for_an_unknown_address_is_kept_and_applied_on_retry(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """The README's promise, which the transaction rollback used to break.

    Stripe retries a non-2xx. Once the person registers, the retry applies.
    """
    await a_plan(db_session)
    event = checkout_event("evt_stranger", "stranger@example.com")

    refused = await post_event(client, event)
    assert refused.status_code == 422
    assert refused.json()["code"] == "invalid_webhook"

    recorded = await billing_repo.event_by_id(db_session, "evt_stranger")
    assert recorded is not None, "the ledger row must survive the refusal"
    assert recorded.processed_at is None
    assert recorded.failure and "No account" in recorded.failure

    await a_customer(db_session, "stranger@example.com")
    retried = await post_event(client, event)
    assert retried.status_code == 200, retried.text
    assert retried.json()["status"] == "applied"
    recorded = await billing_repo.event_by_id(db_session, "evt_stranger")
    assert recorded is not None and recorded.processed_at is not None and recorded.failure is None


async def test_a_plan_with_no_exam_grants_nothing(client: AsyncClient, db_session: AsyncSession) -> None:
    """It used to default to SCA, which is a wrong grant, not a safe one (B-2)."""
    await billing_repo.create_plan(
        db_session, code="vague", stripe_price_id="price_vague", amount_pence=100, duration_days=30
    )
    await db_session.flush()
    await a_customer(db_session, "vague@example.com")
    response = await post_event(
        client, checkout_event("evt_vague", "vague@example.com", price_id="price_vague")
    )
    assert response.status_code == 404
    assert response.json()["code"] == "unknown_plan"


# --------------------------------------------------------------------------
# Receipts: minted with the payment, read back by the customer alone
# --------------------------------------------------------------------------


async def test_a_purchase_mints_a_receipt_the_buyer_can_read(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    from tests.support.tokens import bearer

    await a_plan(db_session)
    buyer = await make_actor("receipt@example.com")
    await post_event(client, checkout_event("evt_r1", "receipt@example.com"))

    listed = await client.get("/api/v1/me/receipts", headers=bearer(buyer))
    assert listed.status_code == 200, listed.text
    assert len(listed.json()["items"]) == 1
    receipt_id = listed.json()["items"][0]

    receipt = await client.get(f"/api/v1/me/receipts/{receipt_id}", headers=bearer(buyer))
    assert receipt.status_code == 200, receipt.text
    body = receipt.json()
    assert body["receipt_id"] == receipt_id
    assert body["customer_email"] == "receipt@example.com"
    assert body["exam_code"] == "sca"
    assert body["amount_total"] == "£24.99"


async def test_a_receipt_is_read_by_its_owner_only(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """The id is short and printed on a document that gets forwarded, so
    holding it must not be enough to read it."""
    from tests.support.tokens import bearer

    await a_plan(db_session)
    buyer = await make_actor("owner@example.com")
    stranger = await make_actor("stranger@example.com")
    await post_event(client, checkout_event("evt_r2", "owner@example.com"))
    receipt_id = (await client.get("/api/v1/me/receipts", headers=bearer(buyer))).json()["items"][0]

    refused = await client.get(f"/api/v1/me/receipts/{receipt_id}", headers=bearer(stranger))
    assert refused.status_code == 404
    assert refused.json()["code"] == "receipt_not_found"
    assert (await client.get("/api/v1/me/receipts", headers=bearer(stranger))).json()["items"] == []

    assert (await client.get("/api/v1/me/receipts")).status_code == 401


async def test_a_payment_taken_before_receipts_existed_is_not_listed(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """`receipt_id` is nullable for payments from before the column existed.
    Those stay Stripe-only until a backfill decides otherwise; a null must not
    surface as an item nothing can render."""
    from datetime import UTC, datetime

    from tests.support.tokens import bearer

    buyer = await make_actor("legacy@example.com")
    user = await identity_repo.user_by_email(db_session, "legacy@example.com")
    assert user is not None
    await billing_repo.record_payment(
        db_session,
        user_id=user.id,
        plan_id=None,
        stripe_payment_intent_id="pi_legacy",
        checkout_session_id=None,
        amount_total_pence=2499,
        currency="gbp",
        receipt_url=None,
        paid_at=datetime.now(UTC),
        entitlement_id=None,
    )
    await db_session.flush()

    listed = await client.get("/api/v1/me/receipts", headers=bearer(buyer))
    assert listed.status_code == 200
    assert listed.json()["items"] == []


async def test_starting_a_checkout_returns_somewhere_to_pay(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """There was no way to start a purchase at all: the platform could take a
    webhook and had nothing that made one arrive."""
    from app.features.billing import service_checkout
    from tests.support.fakes import FakeCheckoutSessions

    await a_plan(db_session)
    token = await make_actor("buyer@example.com")
    fake = FakeCheckoutSessions()
    client._transport.app.dependency_overrides[service_checkout.get_checkout] = lambda: fake  # type: ignore[attr-defined]

    response = await client.post(
        "/api/v1/billing/checkout", json={"plan_code": "one_month"}, headers=bearer(token)
    )
    assert response.status_code == 201, response.text
    assert response.json()["checkout_url"] == fake.url

    # The plan row owns the price. b2c matched the pence paid against a
    # hardcoded table, so a price change broke purchases after the card had
    # been charged.
    assert fake.calls[0]["price_id"] == "price_one_month"
    assert fake.calls[0]["customer_email"] == "buyer@example.com"


async def test_starting_a_checkout_grants_nothing(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Access arrives when the webhook says the money did.

    Somebody who abandons the Stripe page, or never finishes 3-D Secure, has
    started a checkout and bought nothing.
    """
    from sqlalchemy import func, select

    from app.features.billing import service_checkout
    from app.features.entitlements.models import Entitlement
    from tests.support.fakes import FakeCheckoutSessions

    await a_plan(db_session)
    token = await make_actor("abandoner@example.com")
    client._transport.app.dependency_overrides[service_checkout.get_checkout] = (  # type: ignore[attr-defined]
        lambda: FakeCheckoutSessions()
    )

    await client.post("/api/v1/billing/checkout", json={"plan_code": "one_month"}, headers=bearer(token))
    assert await db_session.scalar(select(func.count()).select_from(Entitlement)) == 0


async def test_a_plan_that_is_not_for_sale_is_refused(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from app.features.billing import service_checkout
    from tests.support.fakes import FakeCheckoutSessions

    token = await make_actor("browser@example.com")
    fake = FakeCheckoutSessions()
    client._transport.app.dependency_overrides[service_checkout.get_checkout] = lambda: fake  # type: ignore[attr-defined]

    response = await client.post(
        "/api/v1/billing/checkout", json={"plan_code": "made_up"}, headers=bearer(token)
    )
    assert response.status_code == 404
    assert response.json()["code"] == "plan_not_available"
    # Refused before Stripe was troubled.
    assert not fake.calls


async def test_a_processor_that_is_down_says_try_again(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """503, not 500: it is usually transient, and Stripe's own error text is
    not something to put in front of a customer."""
    from app.features.billing import service_checkout
    from tests.support.fakes import FakeCheckoutSessions

    await a_plan(db_session)
    token = await make_actor("unlucky@example.com")
    client._transport.app.dependency_overrides[service_checkout.get_checkout] = (  # type: ignore[attr-defined]
        lambda: FakeCheckoutSessions(fails=True)
    )

    response = await client.post(
        "/api/v1/billing/checkout", json={"plan_code": "one_month"}, headers=bearer(token)
    )
    assert response.status_code == 503
    assert response.json()["code"] == "checkout_failed"
    assert "stripe is down" not in response.text
