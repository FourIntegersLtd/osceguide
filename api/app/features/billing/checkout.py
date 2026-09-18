"""Starting a payment: the Stripe adapter behind `core.ports.CheckoutSessions`.

Over `httpx` against Stripe's form-encoded REST API rather than through the
`stripe` package. One call, five parameters, a dependency this backend
already has — against a library whose surface is mostly the parts of Stripe
we do not use, and which the webhook side deliberately does without too
(`billing/signature.py` verifies by hand so it is testable with no account).

`mode=payment`, never a subscription. These are fixed-term purchases and the
entitlement model says so: a grant has an end date, and Stripe managing
renewals would make it the authority on access instead.
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
    """The adapter, or a refusal. Never a silent no-op.

    A deployment with no secret key cannot sell, and `STRIPE_SECRET_KEY` is
    deliberately not one of the ten required values — so this is a real state
    a running process can be in, and it has to say so rather than produce a
    checkout that goes nowhere.
    """
    if not settings.stripe_secret_key.strip():
        raise CheckoutUnavailable("STRIPE_SECRET_KEY is not set, so this deployment cannot sell")
    return StripeCheckout(settings.stripe_secret_key)
