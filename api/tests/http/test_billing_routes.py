"""Applying a Stripe delivery, once."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.billing import repository as billing_repo
from app.features.identity import repository as identity_repo
from tests.support.billing import a_plan
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


async def test_a_payment_for_an_unknown_address_is_kept_for_support_not_refused(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """S-4: the customer has paid. A 4xx made Stripe retry for three days and
    then drop the delivery, leaving them charged with no access; it is now
    acknowledged and kept, unprocessed, until it is applied.
    """
    await a_plan(db_session)
    event = checkout_event("evt_stranger", "stranger@example.com")

    kept = await post_event(client, event)
    assert kept.status_code == 200, kept.text
    assert kept.json() == {"status": "needs_attention"}

    recorded = await billing_repo.event_by_id(db_session, "evt_stranger")
    assert recorded is not None, "the ledger row must survive"
    assert recorded.processed_at is None
    assert recorded.failure and "No account" in recorded.failure

    await a_customer(db_session, "stranger@example.com")
    retried = await post_event(client, event)
    assert retried.status_code == 200, retried.text
    assert retried.json()["status"] == "applied"
    recorded = await billing_repo.event_by_id(db_session, "evt_stranger")
    assert recorded is not None and recorded.processed_at is not None and recorded.failure is None


async def test_a_plan_with_no_exam_grants_nothing(client: AsyncClient, db_session: AsyncSession) -> None:
    """It used to default to SCA, which is a wrong grant, not a safe one (B-2).

    The column is NOT NULL now, so the only plan with no exam is one the
    migration found without one: it holds '' and must still be refused.
    """
    await billing_repo.create_plan(
        db_session,
        code="vague",
        stripe_price_id="price_vague",
        amount_pence=100,
        duration_days=30,
        exam_code="",
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

    listed = await client.get("/api/v1/me/receipts-full", headers=bearer(buyer))
    assert listed.status_code == 200, listed.text
    assert len(listed.json()["items"]) == 1
    receipt_id = listed.json()["items"][0]["receipt_id"]

    receipt = await client.get(f"/api/v1/me/receipts/{receipt_id}", headers=bearer(buyer))
    assert receipt.status_code == 200, receipt.text
    body = receipt.json()
    assert body["receipt_id"] == receipt_id
    assert body["customer_email"] == "receipt@example.com"
    assert body["exam_code"] == "sca"
    assert body["amount_total"] == "£24.99"


async def test_receipts_page_by_cursor_and_come_back_whole(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    from tests.support.tokens import bearer

    await a_plan(db_session)
    buyer = await make_actor("pages@example.com")
    for event_id in ("evt_pg1", "evt_pg2", "evt_pg3"):
        await post_event(client, checkout_event(event_id, "pages@example.com"))

    first = (await client.get("/api/v1/me/receipts-full", params={"limit": 2}, headers=bearer(buyer))).json()
    second = (
        await client.get(
            "/api/v1/me/receipts-full",
            params={"limit": 2, "cursor": first["next_cursor"]},
            headers=bearer(buyer),
        )
    ).json()
    assert (len(first["items"]), len(second["items"]), second["next_cursor"]) == (2, 1, None)
    ids = [receipt["receipt_id"] for receipt in first["items"] + second["items"]]
    assert len(set(ids)) == 3
    assert first["items"][0]["amount_total"] == "£24.99"


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
    receipt_id = (await client.get("/api/v1/me/receipts-full", headers=bearer(buyer))).json()["items"][0][
        "receipt_id"
    ]

    refused = await client.get(f"/api/v1/me/receipts/{receipt_id}", headers=bearer(stranger))
    assert refused.status_code == 404
    assert refused.json()["code"] == "receipt_not_found"
    assert (await client.get("/api/v1/me/receipts-full", headers=bearer(stranger))).json()["items"] == []

    assert (await client.get("/api/v1/me/receipts-full")).status_code == 401


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

    listed = await client.get("/api/v1/me/receipts-full", headers=bearer(buyer))
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

    # The cancel URL carries a marker, because Stripe sends a cancel there
    # verbatim and the web has to tell "gave up on checkout" from "typed
    # /pricing" — otherwise every visitor to the pricing page reads
    # "Checkout cancelled".
    assert fake.calls[0]["cancel_url"].endswith("/pricing?cancelled=1")


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


async def test_a_plan_is_sold_only_for_the_buyers_exam(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """An SCA account was offered PLAB and ORTHO beside SCA, and could pay for a
    library every other screen hides from it."""
    from app.features.billing import service_checkout
    from tests.support.fakes import FakeCheckoutSessions

    await a_plan(db_session)
    await ensure_exam(db_session, "plab")
    await billing_repo.create_plan(
        db_session,
        code="plab_one_month",
        stripe_price_id="price_plab_one_month",
        amount_pence=2499,
        duration_days=30,
        exam_code="plab",
    )
    await db_session.flush()
    token = await make_actor("sca-candidate@example.com", exam_code="sca")
    fake = FakeCheckoutSessions()
    client._transport.app.dependency_overrides[service_checkout.get_checkout] = lambda: fake  # type: ignore[attr-defined]

    allowed = await client.post(
        "/api/v1/billing/checkout", json={"plan_code": "one_month"}, headers=bearer(token)
    )
    assert allowed.status_code == 201, allowed.text

    # Last, because a refusal rolls back the test's transaction and the plans with it.
    refused = await client.post(
        "/api/v1/billing/checkout", json={"plan_code": "plab_one_month"}, headers=bearer(token)
    )
    assert refused.status_code == 404
    assert refused.json()["code"] == "plan_not_available"
    assert refused.json()["details"] == {"reason": "not_your_exam"}
    # Stripe was asked for the SCA plan only.
    assert [call["price_id"] for call in fake.calls] == ["price_one_month"]


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


# --- referral discounts -----------------------------------------------------


async def a_plan_with_a_referral_discount(db_session: AsyncSession) -> None:
    """The full-price plan, plus its 10%-off twin as b2c priced it: £24.99 and £22.49."""
    await a_plan(db_session)
    await billing_repo.create_plan(
        db_session,
        code="one_month_referral",
        stripe_price_id="price_one_month_referral",
        amount_pence=2249,
        duration_days=30,
        exam_code="sca",
    )
    await db_session.flush()


async def a_shared_code(client: AsyncClient, make_actor, email: str) -> tuple[str, str]:  # type: ignore[no-untyped-def]
    """A referrer's sign-in token and their code, as they would copy it from their settings."""
    referrer_token = await make_actor(email)
    issued = await client.post("/api/v1/me/referral-code", headers=bearer(referrer_token))
    return referrer_token, str(issued.json()["code"])


async def test_the_plan_list_shows_the_referral_price_on_the_full_price_plan(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """The discounted twin is bought only with a code, so it is not a plan of its own on the page."""
    await a_plan_with_a_referral_discount(db_session)

    response = await client.get("/api/v1/billing/plans")

    assert [
        (plan["code"], plan["amount_pence"], plan["referral_amount_pence"])
        for plan in response.json()["items"]
    ] == [("one_month", 2499, 2249)]


async def test_a_referral_code_buys_at_the_discounted_price(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from app.features.billing import service_checkout
    from tests.support.fakes import FakeCheckoutSessions

    await a_plan_with_a_referral_discount(db_session)
    _, code = await a_shared_code(client, make_actor, "sharer@example.com")
    buyer = await make_actor("discounted@example.com")
    fake = FakeCheckoutSessions()
    client._transport.app.dependency_overrides[service_checkout.get_checkout] = lambda: fake  # type: ignore[attr-defined]

    response = await client.post(
        "/api/v1/billing/checkout",
        json={"plan_code": "one_month", "referral_code": f" {code.lower()} "},
        headers=bearer(buyer),
    )

    assert response.status_code == 201, response.text
    assert fake.calls[0]["price_id"] == "price_one_month_referral"
    assert fake.calls[0]["referral_code"] == code


@pytest.mark.parametrize("whose_code", ["unknown", "own"])
async def test_a_code_that_is_unknown_or_your_own_is_refused_before_stripe(
    client: AsyncClient, make_actor, db_session: AsyncSession, whose_code: str
) -> None:  # type: ignore[no-untyped-def]
    from app.features.billing import service_checkout
    from tests.support.fakes import FakeCheckoutSessions

    await a_plan_with_a_referral_discount(db_session)
    buyer = await make_actor("chancer@example.com")
    code = "NOSUCHCODE"
    if whose_code == "own":
        code = str((await client.post("/api/v1/me/referral-code", headers=bearer(buyer))).json()["code"])
    fake = FakeCheckoutSessions()
    client._transport.app.dependency_overrides[service_checkout.get_checkout] = lambda: fake  # type: ignore[attr-defined]

    response = await client.post(
        "/api/v1/billing/checkout",
        json={"plan_code": "one_month", "referral_code": code},
        headers=bearer(buyer),
    )

    assert response.status_code == 404
    assert response.json()["code"] == "referral_not_found"
    assert not fake.calls


async def test_the_discounted_plan_cannot_be_bought_by_naming_it(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Otherwise 10% off needs no code at all, only a look at the network tab."""
    from app.features.billing import service_checkout
    from tests.support.fakes import FakeCheckoutSessions

    await a_plan_with_a_referral_discount(db_session)
    buyer = await make_actor("sneaky@example.com")
    fake = FakeCheckoutSessions()
    client._transport.app.dependency_overrides[service_checkout.get_checkout] = lambda: fake  # type: ignore[attr-defined]

    response = await client.post(
        "/api/v1/billing/checkout", json={"plan_code": "one_month_referral"}, headers=bearer(buyer)
    )

    assert response.status_code == 404
    assert response.json()["code"] == "plan_not_available"
    assert not fake.calls


async def test_a_plan_with_no_referral_price_refuses_the_code(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Refused rather than charged in full: the customer typed a code expecting 10% off."""
    from app.features.billing import service_checkout
    from tests.support.fakes import FakeCheckoutSessions

    await a_plan(db_session)
    _, code = await a_shared_code(client, make_actor, "sharer-no-discount@example.com")
    buyer = await make_actor("full-price@example.com")
    fake = FakeCheckoutSessions()
    client._transport.app.dependency_overrides[service_checkout.get_checkout] = lambda: fake  # type: ignore[attr-defined]

    response = await client.post(
        "/api/v1/billing/checkout",
        json={"plan_code": "one_month", "referral_code": code},
        headers=bearer(buyer),
    )

    assert response.status_code == 404
    assert response.json()["code"] == "referral_discount_unavailable"
    assert not fake.calls


def referral_checkout_event(event_id: str, email: str, *, price_id: str, referral_code: str) -> dict:
    """A completed checkout that was started with a referral code."""
    event = checkout_event(event_id, email, price_id=price_id)
    event["data"]["object"]["metadata"]["referral_code"] = referral_code
    event["data"]["object"]["amount_total"] = 2249
    return event


async def test_a_paid_referral_purchase_grants_access_and_credits_the_referrer(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from app.features.entitlements import repository as ent_repo

    await a_plan_with_a_referral_discount(db_session)
    referrer_token, code = await a_shared_code(client, make_actor, "earner@example.com")
    await a_customer(db_session, "referred-buyer@example.com")

    response = await post_event(
        client,
        referral_checkout_event(
            "evt_referral_1",
            "referred-buyer@example.com",
            price_id="price_one_month_referral",
            referral_code=code,
        ),
    )

    assert response.json()["status"] == "applied"
    buyer = await identity_repo.user_by_email(db_session, "referred-buyer@example.com")
    assert buyer is not None
    assert [grant.source for grant in await ent_repo.for_user(db_session, buyer.id)] == ["purchase"]
    mine = await client.get("/api/v1/me/referrals", headers=bearer(referrer_token))
    assert mine.json() == {"code": code, "redeemed_count": 1, "earned_pence": 250}


async def test_a_referral_purchase_tells_the_referrer_what_they_earned_without_naming_the_buyer(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from sqlalchemy import select

    from app.features.notifications.models import OutboundMessage

    await a_plan_with_a_referral_discount(db_session)
    _, code = await a_shared_code(client, make_actor, "told@example.com")
    await a_customer(db_session, "told-buyer@example.com")

    await post_event(
        client,
        referral_checkout_event(
            "evt_told_1", "told-buyer@example.com", price_id="price_one_month_referral", referral_code=code
        ),
    )

    messages = list(
        (
            await db_session.execute(
                select(OutboundMessage).where(OutboundMessage.template_key == "referral_redeemed")
            )
        ).scalars()
    )
    assert [(m.recipient, m.payload) for m in messages] == [("told@example.com", {"earned": "£2.50"})]


async def test_a_full_price_payment_carrying_a_code_credits_nobody(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Only a discounted plan proves the checkout went through the code check."""
    await a_plan_with_a_referral_discount(db_session)
    referrer_token, code = await a_shared_code(client, make_actor, "not-earner@example.com")
    await a_customer(db_session, "full-payer@example.com")

    response = await post_event(
        client,
        referral_checkout_event(
            "evt_referral_2", "full-payer@example.com", price_id="price_one_month", referral_code=code
        ),
    )

    assert response.json()["status"] == "applied"
    mine = await client.get("/api/v1/me/referrals", headers=bearer(referrer_token))
    assert mine.json()["redeemed_count"] == 0


async def test_a_code_that_stopped_resolving_still_grants_what_was_paid_for(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """The customer has paid. A referral problem must never cost them their access."""
    from app.features.entitlements import repository as ent_repo

    await a_plan_with_a_referral_discount(db_session)
    await a_customer(db_session, "orphan-code@example.com")

    response = await post_event(
        client,
        referral_checkout_event(
            "evt_referral_3",
            "orphan-code@example.com",
            price_id="price_one_month_referral",
            referral_code="GONE1234",
        ),
    )

    assert response.json()["status"] == "applied"
    buyer = await identity_repo.user_by_email(db_session, "orphan-code@example.com")
    assert buyer is not None
    assert len(await ent_repo.for_user(db_session, buyer.id)) == 1


async def test_a_second_checkout_for_an_exam_already_paid_for_is_refused_before_stripe(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Nothing checked what the buyer already held, so a second tab, a double click or a
    stale page took a second payment for access they had (A-17)."""
    from datetime import UTC, datetime, timedelta

    from app.features.billing import service_checkout
    from app.features.entitlements import repository as ent_repo
    from tests.support.fakes import FakeCheckoutSessions

    await a_plan(db_session)
    token = await make_actor("twice@example.com")
    paid = await post_event(client, checkout_event("evt_twice", "twice@example.com"))
    assert paid.json()["status"] == "applied"
    fake = FakeCheckoutSessions()
    client._transport.app.dependency_overrides[service_checkout.get_checkout] = lambda: fake  # type: ignore[attr-defined]

    refused = await client.post(
        "/api/v1/billing/checkout", json={"plan_code": "one_month"}, headers=bearer(token)
    )
    assert refused.status_code == 409, refused.text
    assert refused.json()["code"] == "already_purchased"
    assert fake.calls == []

    # Once the purchase has lapsed, buying again is how access is renewed.
    user = await identity_repo.user_by_email(db_session, "twice@example.com")
    assert user is not None
    for grant in await ent_repo.for_user(db_session, user.id):
        await ent_repo.set_ends_at(db_session, grant.id, ends_at=datetime.now(UTC) - timedelta(days=1))
    await db_session.commit()
    again = await client.post(
        "/api/v1/billing/checkout", json={"plan_code": "one_month"}, headers=bearer(token)
    )
    assert again.status_code == 201, again.text


async def test_the_idempotency_key_reaches_the_processor_scoped_to_the_buyer(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from app.features.billing import service_checkout
    from tests.support.fakes import FakeCheckoutSessions

    await a_plan(db_session)
    token = await make_actor("keyed@example.com")
    user = await identity_repo.user_by_email(db_session, "keyed@example.com")
    assert user is not None
    fake = FakeCheckoutSessions()
    client._transport.app.dependency_overrides[service_checkout.get_checkout] = lambda: fake  # type: ignore[attr-defined]

    for _ in range(2):
        response = await client.post(
            "/api/v1/billing/checkout",
            json={"plan_code": "one_month"},
            headers={**bearer(token), "Idempotency-Key": "click-1"},
        )
        assert response.status_code == 201, response.text
    assert [call["idempotency_key"] for call in fake.calls] == [f"checkout:{user.id}:click-1"] * 2


async def test_the_receipts_for_one_checkout_session_are_found_by_its_id(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """The page Stripe returns to knows the session, not the receipt: it asks whether this
    session has been paid, and only its own buyer can see the answer."""
    from tests.support.tokens import bearer

    await a_plan(db_session)
    buyer = await make_actor("session@example.com")
    stranger = await make_actor("not-the-buyer@example.com")
    await post_event(client, checkout_event("evt_cs", "session@example.com"))
    path = "/api/v1/me/receipts-full"

    mine = await client.get(path, params={"checkout_session_id": "cs_test_1"}, headers=bearer(buyer))
    assert len(mine.json()["items"]) == 1
    other = await client.get(path, params={"checkout_session_id": "cs_unpaid"}, headers=bearer(buyer))
    assert other.json()["items"] == []
    theirs = await client.get(path, params={"checkout_session_id": "cs_test_1"}, headers=bearer(stranger))
    assert theirs.json()["items"] == []


# --- S-13: a refund or a dispute takes the access back --------------------------------


def charge_event(event_id: str, event_type: str, intent: str, *, fully_refunded: bool = True) -> dict:
    """A `charge.refunded` or `charge.dispute.created` delivery naming the payment intent."""
    if event_type == "charge.dispute.created":
        return {"id": event_id, "type": event_type, "data": {"object": {"payment_intent": intent}}}
    return {
        "id": event_id,
        "type": event_type,
        "data": {
            "object": {
                "payment_intent": intent,
                "amount": 2249,
                "amount_refunded": 2249 if fully_refunded else 500,
                "refunded": fully_refunded,
            }
        },
    }


async def _bought_with_a_code(client: AsyncClient, make_actor, db_session: AsyncSession, who: str):  # type: ignore[no-untyped-def]
    from app.features.entitlements import repository as ent_repo

    await a_plan_with_a_referral_discount(db_session)
    referrer_token, code = await a_shared_code(client, make_actor, f"{who}-referrer@example.com")
    await a_customer(db_session, f"{who}-buyer@example.com")
    event_id = f"evt_{who}_checkout"
    await post_event(
        client,
        referral_checkout_event(
            event_id, f"{who}-buyer@example.com", price_id="price_one_month_referral", referral_code=code
        ),
    )
    buyer = await identity_repo.user_by_email(db_session, f"{who}-buyer@example.com")
    assert buyer is not None
    return referrer_token, buyer, f"pi_{event_id}", ent_repo


async def test_a_full_refund_withdraws_the_access_and_the_referral_credit(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    referrer_token, buyer, intent, ent_repo = await _bought_with_a_code(
        client, make_actor, db_session, "refund"
    )
    before = await client.get("/api/v1/me/referrals", headers=bearer(referrer_token))
    assert before.json()["earned_pence"] == 250

    response = await post_event(client, charge_event("evt_refund_1", "charge.refunded", intent))

    assert response.json()["status"] == "applied"
    grants = await ent_repo.for_user(db_session, buyer.id)
    assert [g.revoked_at is not None for g in grants] == [True]
    after = await client.get("/api/v1/me/referrals", headers=bearer(referrer_token))
    assert after.json()["earned_pence"] == 0


async def test_a_dispute_withdraws_the_access(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    _, buyer, intent, ent_repo = await _bought_with_a_code(client, make_actor, db_session, "dispute")

    response = await post_event(client, charge_event("evt_dispute_1", "charge.dispute.created", intent))

    assert response.json()["status"] == "applied"
    assert [g.revoked_at is not None for g in await ent_repo.for_user(db_session, buyer.id)] == [True]


async def test_a_partial_refund_leaves_the_access(client: AsyncClient, db_session: AsyncSession) -> None:
    from app.features.entitlements import repository as ent_repo

    await a_plan(db_session)
    await a_customer(db_session, "partial@example.com")
    await post_event(client, checkout_event("evt_partial_co", "partial@example.com"))

    response = await post_event(
        client, charge_event("evt_partial_1", "charge.refunded", "pi_evt_partial_co", fully_refunded=False)
    )

    assert response.json()["status"] == "ignored"
    user = await identity_repo.user_by_email(db_session, "partial@example.com")
    assert user is not None
    assert [g.revoked_at for g in await ent_repo.for_user(db_session, user.id)] == [None]


async def test_a_refund_that_arrives_before_its_checkout_is_retried_not_lost(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.features.entitlements import repository as ent_repo

    await a_plan(db_session)
    await a_customer(db_session, "early@example.com")
    # Committed: the refused delivery rolls its request's transaction back, setup included.
    await db_session.commit()
    refund = charge_event("evt_early_refund", "charge.refunded", "pi_evt_early_co")

    first = await post_event(client, refund)
    assert first.status_code == 404
    assert first.json()["code"] == "payment_not_yet_recorded"
    stored = await billing_repo.event_by_id(db_session, "evt_early_refund")
    assert stored is not None, "the refused delivery left no ledger row"
    assert stored.processed_at is None
    assert stored.failure is not None

    checkout = await post_event(client, checkout_event("evt_early_co", "early@example.com"))
    assert checkout.json()["status"] == "applied", checkout.text
    second = await post_event(client, refund)

    assert second.status_code == 200, second.text
    assert second.json()["status"] == "applied"
    user = await identity_repo.user_by_email(db_session, "early@example.com")
    assert user is not None
    assert [g.revoked_at is not None for g in await ent_repo.for_user(db_session, user.id)] == [True]


async def _buy_again_with_the_code(client: AsyncClient, event_id: str, who: str, code: str) -> None:
    await post_event(
        client,
        referral_checkout_event(
            event_id, f"{who}-buyer@example.com", price_id="price_one_month_referral", referral_code=code
        ),
    )


async def test_a_dispute_on_one_purchase_takes_back_only_that_purchases_credit(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    referrer_token, _, first_intent, _ = await _bought_with_a_code(client, make_actor, db_session, "twice")
    code = (await client.get("/api/v1/me/referrals", headers=bearer(referrer_token))).json()["code"]
    await _buy_again_with_the_code(client, "evt_twice_second", "twice", code)
    earned = lambda: client.get("/api/v1/me/referrals", headers=bearer(referrer_token))  # noqa: E731
    assert (await earned()).json()["earned_pence"] == 500

    await post_event(
        client, charge_event("evt_twice_dispute", "charge.dispute.created", "pi_evt_twice_second")
    )
    assert (await earned()).json()["earned_pence"] == 250

    # The same payment disputed and then refunded: the second withdrawal takes nothing more.
    await post_event(client, charge_event("evt_twice_refund", "charge.refunded", "pi_evt_twice_second"))
    assert (await earned()).json()["earned_pence"] == 250

    await post_event(client, charge_event("evt_twice_first", "charge.refunded", first_intent))
    assert (await earned()).json()["earned_pence"] == 0


async def test_a_grant_revoked_by_hand_does_not_stop_a_dispute_taking_back_the_credit(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from datetime import UTC, datetime

    referrer_token, buyer, intent, ent_repo = await _bought_with_a_code(
        client, make_actor, db_session, "hand"
    )
    for grant in await ent_repo.for_user(db_session, buyer.id):
        await ent_repo.revoke(db_session, grant.id, at=datetime.now(UTC))
    await db_session.commit()

    await post_event(client, charge_event("evt_hand_dispute", "charge.dispute.created", intent))

    earned = await client.get("/api/v1/me/referrals", headers=bearer(referrer_token))
    assert earned.json()["earned_pence"] == 0


async def test_a_refund_after_a_dispute_on_the_same_payment_is_ignored(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    _, _, intent, _ = await _bought_with_a_code(client, make_actor, db_session, "ignored")

    first = await post_event(client, charge_event("evt_ignored_dispute", "charge.dispute.created", intent))
    second = await post_event(client, charge_event("evt_ignored_refund", "charge.refunded", intent))

    assert first.json()["status"] == "applied"
    assert second.json()["status"] == "ignored"


def dispute_closed_event(event_id: str, intent: str, outcome: str) -> dict:
    return {
        "id": event_id,
        "type": "charge.dispute.closed",
        "data": {"object": {"payment_intent": intent, "status": outcome}},
    }


async def test_a_dispute_won_restores_the_access_and_the_credit(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    referrer_token, buyer, intent, ent_repo = await _bought_with_a_code(client, make_actor, db_session, "won")
    await post_event(client, charge_event("evt_won_open", "charge.dispute.created", intent))

    response = await post_event(client, dispute_closed_event("evt_won_close", intent, "won"))

    assert response.json()["status"] == "applied"
    assert [g.revoked_at for g in await ent_repo.for_user(db_session, buyer.id)] == [None]
    earned = await client.get("/api/v1/me/referrals", headers=bearer(referrer_token))
    assert earned.json()["earned_pence"] == 250


async def test_a_dispute_lost_leaves_the_access_withdrawn(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    _, buyer, intent, ent_repo = await _bought_with_a_code(client, make_actor, db_session, "lost")
    await post_event(client, charge_event("evt_lost_open", "charge.dispute.created", intent))

    response = await post_event(client, dispute_closed_event("evt_lost_close", intent, "lost"))

    assert response.json()["status"] == "ignored"
    assert [g.revoked_at is not None for g in await ent_repo.for_user(db_session, buyer.id)] == [True]


async def test_a_refund_after_the_credit_was_paid_out_records_a_negative_balance_once(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from datetime import UTC, datetime

    from app.features.growth import repository as growth_repo

    referrer_token, _, intent, _ = await _bought_with_a_code(client, make_actor, db_session, "paidout")
    referrer = await identity_repo.user_by_email(db_session, "paidout-referrer@example.com")
    assert referrer is not None
    credit = next(r for r in await growth_repo.referrals_for(db_session, referrer.id) if r.earned_pence)
    await growth_repo.set_payout(
        db_session,
        credit.id,
        payout_status="paid",
        payout_reference="BANK-1",
        paid_at=datetime.now(UTC),
        paid_by_user_id=None,
    )
    await db_session.commit()

    refunded = await post_event(client, charge_event("evt_paid_refund", "charge.refunded", intent))
    await post_event(client, charge_event("evt_paid_dispute", "charge.dispute.created", intent))

    assert refunded.json()["status"] == "applied"
    balance = await client.get("/api/v1/me/referrals", headers=bearer(referrer_token))
    # 250 earned and paid, 250 taken back once: the referrer owes nothing and is owed nothing.
    assert balance.json()["earned_pence"] == 0
    rows = [r for r in await growth_repo.referrals_for(db_session, referrer.id) if r.redeemed_at]
    assert sorted((r.earned_pence, r.payout_status) for r in rows) == [(-250, "unpaid"), (250, "paid")]


async def test_a_dispute_won_after_a_paid_out_credit_was_clawed_back_reverses_the_negative_row(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """S-13: the referrer was paid for a sale that stood after all, so the negative row goes."""
    from datetime import UTC, datetime

    from app.features.growth import repository as growth_repo

    referrer_token, _, intent, _ = await _bought_with_a_code(client, make_actor, db_session, "wonpaid")
    referrer = await identity_repo.user_by_email(db_session, "wonpaid-referrer@example.com")
    assert referrer is not None
    credit = next(r for r in await growth_repo.referrals_for(db_session, referrer.id) if r.earned_pence)
    await growth_repo.set_payout(
        db_session,
        credit.id,
        payout_status="paid",
        payout_reference="BANK-2",
        paid_at=datetime.now(UTC),
        paid_by_user_id=None,
    )
    await db_session.commit()
    await post_event(client, charge_event("evt_wonpaid_open", "charge.dispute.created", intent))
    rows = [r for r in await growth_repo.referrals_for(db_session, referrer.id) if r.redeemed_at]
    assert sorted(r.earned_pence for r in rows) == [-250, 250]

    response = await post_event(client, dispute_closed_event("evt_wonpaid_close", intent, "won"))

    assert response.json()["status"] == "applied"
    rows = [r for r in await growth_repo.referrals_for(db_session, referrer.id) if r.redeemed_at]
    # Review of fc59828: the clawback is voided, not deleted, so the ledger keeps the history.
    assert sorted((r.earned_pence, r.payout_status) for r in rows) == [(0, "unpaid"), (250, "paid")]
    balance = await client.get("/api/v1/me/referrals", headers=bearer(referrer_token))
    assert balance.json()["earned_pence"] == 250


async def test_a_different_plan_is_bought_while_one_is_live_and_extends_from_the_current_end(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """A-24: the same plan again stays refused, with a message that says what to do; a different
    plan is allowed and its access starts where the live one ends, so nothing paid for is lost."""
    from datetime import timedelta

    from app.features.billing import service_checkout
    from app.features.entitlements import repository as ent_repo
    from tests.support.fakes import FakeCheckoutSessions

    await a_plan(db_session)
    await billing_repo.create_plan(
        db_session,
        code="three_month",
        stripe_price_id="price_three_month",
        amount_pence=5999,
        duration_days=90,
        exam_code="sca",
    )
    await db_session.flush()
    token = await make_actor("upgrade@example.com")
    assert (await post_event(client, checkout_event("evt_up_1", "upgrade@example.com"))).json()[
        "status"
    ] == "applied"
    fake = FakeCheckoutSessions()
    client._transport.app.dependency_overrides[service_checkout.get_checkout] = lambda: fake  # type: ignore[attr-defined]

    same = await client.post(
        "/api/v1/billing/checkout", json={"plan_code": "one_month"}, headers=bearer(token)
    )
    assert same.status_code == 409, same.text
    assert same.json()["code"] == "already_purchased"
    assert same.json()["message"] == (
        "You already have this plan. Choose a different plan to extend your access, "
        "or buy it again when it ends."
    )
    assert fake.calls == []

    different = await client.post(
        "/api/v1/billing/checkout", json={"plan_code": "three_month"}, headers=bearer(token)
    )
    assert different.status_code == 201, different.text

    paid = await post_event(client, checkout_event("evt_up_2", "upgrade@example.com", "price_three_month"))
    assert paid.json()["status"] == "applied"
    user = await identity_repo.user_by_email(db_session, "upgrade@example.com")
    assert user is not None
    first, second = sorted(await ent_repo.for_user(db_session, user.id), key=lambda grant: grant.created_at)
    assert first.ends_at is not None
    assert second.starts_at == first.ends_at
    assert second.ends_at == first.ends_at + timedelta(days=90)
    payment = await billing_repo.payment_by_intent(db_session, "pi_evt_up_2")
    assert payment is not None
    assert payment.plan_starts_at == first.ends_at
    assert payment.plan_ends_at == first.ends_at + timedelta(days=90)

    # The extension is held too: the same plan is still refused while it is, and so is the new one.
    again = await client.post(
        "/api/v1/billing/checkout", json={"plan_code": "three_month"}, headers=bearer(token)
    )
    assert again.status_code == 409, again.text


async def test_two_events_for_one_payment_intent_grant_once(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Different event ids can carry the same payment intent; the second must not stack a grant."""
    from app.features.entitlements import repository as ent_repo

    await a_plan(db_session)
    await a_customer(db_session, "twoevents@example.com")
    first = checkout_event("evt_dup_a", "twoevents@example.com")
    second = checkout_event("evt_dup_b", "twoevents@example.com")
    second["data"]["object"]["payment_intent"] = first["data"]["object"]["payment_intent"]

    assert (await post_event(client, first)).json()["status"] == "applied"
    await post_event(client, second)

    user = await identity_repo.user_by_email(db_session, "twoevents@example.com")
    assert user is not None
    assert len(await ent_repo.for_user(db_session, user.id)) == 1


async def test_refunding_the_first_plan_pulls_a_stacked_plan_forward(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """A-25: the stacked grant starts when the refunded one ended, so refunding the first leaves
    a gap unless the later grant moves to start now."""
    from datetime import UTC, datetime, timedelta

    from app.features.entitlements import repository as ent_repo

    await a_plan(db_session)
    await billing_repo.create_plan(
        db_session,
        code="three_month",
        stripe_price_id="price_three_month",
        amount_pence=5999,
        duration_days=90,
        exam_code="sca",
    )
    await a_customer(db_session, "gap@example.com")
    await post_event(client, checkout_event("evt_gap_1", "gap@example.com"))
    await post_event(client, checkout_event("evt_gap_2", "gap@example.com", "price_three_month"))
    user = await identity_repo.user_by_email(db_session, "gap@example.com")
    assert user is not None
    first, second = sorted(await ent_repo.for_user(db_session, user.id), key=lambda grant: grant.created_at)
    assert second.starts_at == first.ends_at

    refunded = await post_event(client, charge_event("evt_gap_r", "charge.refunded", "pi_evt_gap_1"))
    assert refunded.json()["status"] == "applied"

    await db_session.refresh(first)
    await db_session.refresh(second)
    assert first.revoked_at is not None
    assert second.revoked_at is None
    now = datetime.now(UTC)
    assert abs(second.starts_at - now) < timedelta(minutes=5)
    assert second.ends_at - second.starts_at == timedelta(days=90)


async def test_a_dispute_won_puts_a_pulled_forward_plan_back_behind_the_restored_one(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Review of S-13: the stacked plan was pulled forward when the first was disputed; once the
    first is back, the two must not overlap or the buyer loses the overlapping days."""
    from datetime import timedelta

    from app.features.entitlements import repository as ent_repo

    await a_plan(db_session)
    await billing_repo.create_plan(
        db_session,
        code="three_month",
        stripe_price_id="price_three_month",
        amount_pence=5999,
        duration_days=90,
        exam_code="sca",
    )
    await a_customer(db_session, "overlap@example.com")
    await post_event(client, checkout_event("evt_ov_1", "overlap@example.com"))
    await post_event(client, checkout_event("evt_ov_2", "overlap@example.com", "price_three_month"))
    user = await identity_repo.user_by_email(db_session, "overlap@example.com")
    assert user is not None
    first, second = sorted(await ent_repo.for_user(db_session, user.id), key=lambda grant: grant.ends_at)
    await post_event(client, charge_event("evt_ov_open", "charge.dispute.created", "pi_evt_ov_1"))

    won = await post_event(client, dispute_closed_event("evt_ov_close", "pi_evt_ov_1", "won"))

    assert won.json()["status"] == "applied"
    await db_session.refresh(first)
    await db_session.refresh(second)
    assert first.revoked_at is None
    assert second.starts_at == first.ends_at
    assert second.ends_at == first.ends_at + timedelta(days=90)


async def test_a_dispute_won_does_not_restore_access_support_had_already_revoked(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Review of S-13: the dispute did not withdraw this grant, so winning it must not give it back."""
    from datetime import UTC, datetime

    referrer_token, buyer, intent, ent_repo = await _bought_with_a_code(
        client, make_actor, db_session, "abuse"
    )
    for grant in await ent_repo.for_user(db_session, buyer.id):
        await ent_repo.revoke(db_session, grant.id, at=datetime.now(UTC))
    await db_session.commit()
    await post_event(client, charge_event("evt_abuse_open", "charge.dispute.created", intent))

    await post_event(client, dispute_closed_event("evt_abuse_close", intent, "won"))

    assert [g.revoked_at is not None for g in await ent_repo.for_user(db_session, buyer.id)] == [True]


async def test_a_dispute_won_after_the_payment_was_refunded_restores_nothing(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Review of S-13: the money went back by refund, so neither the access nor the credit returns."""
    referrer_token, buyer, intent, ent_repo = await _bought_with_a_code(
        client, make_actor, db_session, "refwon"
    )
    await post_event(client, charge_event("evt_refwon_open", "charge.dispute.created", intent))
    await post_event(client, charge_event("evt_refwon_refund", "charge.refunded", intent))

    won = await post_event(client, dispute_closed_event("evt_refwon_close", intent, "won"))

    assert won.json()["status"] == "ignored"
    assert [g.revoked_at is not None for g in await ent_repo.for_user(db_session, buyer.id)] == [True]
    earned = await client.get("/api/v1/me/referrals", headers=bearer(referrer_token))
    assert earned.json()["earned_pence"] == 0


async def test_a_clawback_row_is_not_a_redeemed_referral_and_is_netted_in_the_queue(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Review of S-13: the negative row nets the balance but is not a second referral."""
    from datetime import UTC, datetime

    from app.features.growth import repository as growth_repo
    from app.features.growth import service_payouts

    referrer_token, _, intent, _ = await _bought_with_a_code(client, make_actor, db_session, "netted")
    referrer = await identity_repo.user_by_email(db_session, "netted-referrer@example.com")
    assert referrer is not None
    credit = next(r for r in await growth_repo.referrals_for(db_session, referrer.id) if r.earned_pence)
    await growth_repo.set_payout(
        db_session,
        credit.id,
        payout_status="paid",
        payout_reference="BANK-3",
        paid_at=datetime.now(UTC),
        paid_by_user_id=None,
    )
    await db_session.commit()

    await post_event(client, charge_event("evt_netted_refund", "charge.refunded", intent))

    balance = (await client.get("/api/v1/me/referrals", headers=bearer(referrer_token))).json()
    assert (balance["redeemed_count"], balance["earned_pence"]) == (1, 0)
    owed = await service_payouts.owed_total(db_session)
    assert (owed.owed_pence, owed.referrals) == (-250, 0)


async def test_a_plan_says_how_many_stations_its_exam_has_published(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from tests.support.library import publish_library_station

    await a_plan(db_session)
    await billing_repo.create_plan(
        db_session,
        code="plab_month",
        stripe_price_id="price_plab",
        amount_pence=999,
        duration_days=30,
        exam_code="plab",
    )
    await publish_library_station(db_session, "sca")
    await publish_library_station(db_session, "sca")
    await db_session.flush()

    items = (await client.get("/api/v1/billing/plans")).json()["items"]
    assert {plan["exam_code"]: plan["station_count"] for plan in items} == {"sca": 2, "plab": 0}


async def test_a_checkout_finds_its_payer_by_user_id_after_an_email_change(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """The address Stripe echoes is the one at checkout; the person may have changed it since."""
    from app.features.entitlements import repository as ent_repo

    await a_plan(db_session)
    await a_customer(db_session, "moved@example.com")
    user = await identity_repo.user_by_email(db_session, "moved@example.com")
    assert user is not None
    await identity_repo.set_email(db_session, user.id, "moved-on@example.com")
    event = checkout_event("evt_moved", "moved@example.com")
    event["data"]["object"]["client_reference_id"] = str(user.id)

    response = await post_event(client, event)
    assert response.json()["status"] == "applied"
    assert [g.source for g in await ent_repo.for_user(db_session, user.id)] == ["purchase"]
