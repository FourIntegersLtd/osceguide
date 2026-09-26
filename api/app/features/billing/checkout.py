"""Starting a payment: the Stripe adapter behind `core.ports.CheckoutSessions`.

Over `httpx` against Stripe's form-encoded REST API rather than the `stripe` package — one
call, five parameters, no new dependency.

`mode=payment`, never a subscription: these are fixed-term purchases and a grant has an end
date, so Stripe managing renewals would make it the authority on access instead.
"""

from __future__ import annotations

import httpx

from app.core.logging import get_logger
from app.core.ports import CheckoutUnavailable
from app.core.settings import Settings

log = get_logger(__name__)

STRIPE_CHECKOUT_URL = "https://api.stripe.com/v1/checkout/sessions"
TIMEOUT_SECONDS = 15.0


class StripeCheckout:

    def __init__(self, secret_key: str) -> None:
        self._secret_key = secret_key

    async def create(
        self,
        *,
        price_id: str,
        customer_email: str,
        success_url: str,
        cancel_url: str,
        client_reference: str,
    ) -> str:
        form = {
            "mode": "payment",
            "line_items[0][price]": price_id,
            "line_items[0][quantity]": "1",
            "customer_email": customer_email,
            "success_url": success_url,
            "cancel_url": cancel_url,
            # Ties the completed webhook back to the person who started it,
            # without trusting anything the browser sends back.
            "client_reference_id": client_reference,
            # SEC-017: the completed-checkout webhook resolves the plan from
            # `metadata.price_id` (see billing/service.py::_price_id). Without
            # this, a real webhook arrives with no price and every genuine
            # payment is refused as InvalidWebhook. Stripe echoes metadata back
            # on the session object verbatim.
            "metadata[price_id]": price_id,
        }
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
                response = await client.post(STRIPE_CHECKOUT_URL, data=form, auth=(self._secret_key, ""))
        except httpx.HTTPError as exc:
            raise CheckoutUnavailable(f"could not reach Stripe: {exc}") from exc

        if response.status_code >= 400:
            # Logged with the status and Stripe's own message, never returned:
            # the customer gets "we could not start this", because a card
            # processor's error text is not something to put in front of them.
            log.warning("stripe refused a checkout", status=response.status_code, body=response.text[:500])
            raise CheckoutUnavailable(f"Stripe refused the checkout ({response.status_code})")

        url = response.json().get("url")
        if not url:
            raise CheckoutUnavailable("Stripe returned a checkout with no URL")
        return str(url)


def build_checkout(settings: Settings) -> StripeCheckout:
    """The adapter, or a refusal — never a silent no-op. `STRIPE_SECRET_KEY` is not one of the
    required settings, so a deployment with none must say so rather than produce a dead checkout."""
    if not settings.stripe_secret_key.strip():
        raise CheckoutUnavailable("STRIPE_SECRET_KEY is not set, so this deployment cannot sell")
    return StripeCheckout(settings.stripe_secret_key)
