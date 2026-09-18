"""Starting a payment.

Split from `service.py`, which finishes one. The two halves never call each
other and have opposite risks: this one must grant nothing, and that one must
grant exactly once. Keeping them apart is also what kept `service.py` under
the file cap.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.ports import CheckoutSessions, CheckoutUnavailable
from app.core.settings import Settings, SettingsDep
from app.features.billing import errors, repository

log = get_logger(__name__)


def get_checkout(settings: SettingsDep) -> CheckoutSessions:
    """The adapter, as the router's dependency. Overridden in tests with a fake.

    `SettingsDep` rather than a bare `Settings`: FastAPI reads a dependency's
    own signature, and an un-annotated pydantic model there is taken for a
    second request body — which made every call to this route answer 422
    asking for a field called `body`.
    """
    from app.features.billing.checkout import build_checkout  # noqa: PLC0415

    try:
        return build_checkout(settings)
    except CheckoutUnavailable as exc:
        raise errors.CheckoutFailed() from exc


async def start_checkout(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    email: str,
    plan_code: str,
    checkout: CheckoutSessions,
    settings: Settings,
) -> str:
    """Send this person to pay for a plan, and return where to send them.

    The client names a **plan code**, never a price or an amount. b2c matched
    the pence paid against a hardcoded table and raised `Invalid amount paid`
    on a miss, so a price change, a coupon or another currency broke the
    purchase *after* the card was charged. Here the plan row owns the price
    and Stripe is told which one to use.

    Nothing is granted here and no payment is recorded. Access arrives when
    the webhook says the money did: a customer who abandons the Stripe page,
    or who never completes 3-D Secure, has started a checkout and bought
    nothing, and this route must not be able to say otherwise.
    """
    plan = await repository.plan_by_code(session, plan_code)
    if plan is None:
        raise errors.PlanNotAvailable()

    base = settings.frontend_url.rstrip("/")
    try:
        return await checkout.create(
            price_id=plan.stripe_price_id,
            customer_email=email,
            success_url=f"{base}/billing/complete?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{base}/pricing",
            client_reference=str(user_id),
        )
    except CheckoutUnavailable as exc:
        # The processor's own words go to the log, never to the customer.
        log.warning("checkout could not be started", plan=plan_code, error=str(exc))
        raise errors.CheckoutFailed() from exc
