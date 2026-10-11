"""SEC-017: a checkout session carries the `metadata.price_id` its webhook needs.

The completed-checkout webhook resolves the plan from `metadata.price_id`.
Billing tests build that event by hand, so they cannot catch a checkout that
never sends it; this asserts on the form actually posted to Stripe.
"""

from __future__ import annotations

from urllib.parse import parse_qs

import httpx
import pytest

from app.features.billing import checkout


async def test_the_checkout_form_sends_the_price_id_as_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: dict[str, list[str]] = {}

    def stripe(request: httpx.Request) -> httpx.Response:
        sent.update(parse_qs(request.content.decode()))
        return httpx.Response(200, json={"url": "https://checkout.stripe.test/c/pay"})

    real_client = httpx.AsyncClient

    def fake_client(*args: object, **kwargs: object) -> httpx.AsyncClient:
        kwargs["transport"] = httpx.MockTransport(stripe)
        return real_client(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(checkout.httpx, "AsyncClient", fake_client)

    await checkout.StripeCheckout("sk_test_x").create(
        price_id="price_123",
        customer_email="buyer@example.com",
        success_url="https://app.test/ok",
        cancel_url="https://app.test/cancel",
        client_reference="ref-1",
        referral_code=None,
    )

    assert sent["metadata[price_id]"] == ["price_123"]
    assert sent["line_items[0][price]"] == ["price_123"]
    # A one-off payment, never a Stripe subscription: nothing renews, so closing an account
    # has nothing in Stripe to cancel (A-34). A change to `subscription` must teach
    # `identity.service_close_account.close_account` to cancel it first.
    assert sent["mode"] == ["payment"]
    # A full-price checkout credits nobody, so it carries no code.
    assert "metadata[referral_code]" not in sent


async def test_a_referral_checkout_carries_its_code_for_the_webhook(monkeypatch: pytest.MonkeyPatch) -> None:
    """The webhook credits the referrer from `metadata.referral_code`. Without it
    on the form, every discounted sale would credit nobody."""
    sent: dict[str, list[str]] = {}

    def stripe(request: httpx.Request) -> httpx.Response:
        sent.update(parse_qs(request.content.decode()))
        return httpx.Response(200, json={"url": "https://checkout.stripe.test/c/pay"})

    real_client = httpx.AsyncClient

    def fake_client(*args: object, **kwargs: object) -> httpx.AsyncClient:
        kwargs["transport"] = httpx.MockTransport(stripe)
        return real_client(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(checkout.httpx, "AsyncClient", fake_client)

    await checkout.StripeCheckout("sk_test_x").create(
        price_id="price_discounted",
        customer_email="buyer@example.com",
        success_url="https://app.test/ok",
        cancel_url="https://app.test/cancel",
        client_reference="ref-1",
        referral_code="FRIEND42",
    )

    assert sent["metadata[referral_code]"] == ["FRIEND42"]
    assert sent["line_items[0][price]"] == ["price_discounted"]
