"""Starting a payment.

The counterpart to `service.py`, which finishes one. The two halves never call each other and
have opposite risks: this one must grant nothing, and that one must grant exactly once.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.ports import CheckoutSessions, CheckoutUnavailable
from app.core.settings import Settings, SettingsDep
from app.features.billing import domain, errors, repository
from app.features.entitlements import service as entitlements
from app.features.entitlements import service_access
from app.features.growth import service as growth

log = get_logger(__name__)


def get_checkout(settings: SettingsDep) -> CheckoutSessions:
    """The adapter, as the router's dependency. Overridden in tests with a fake.

    `SettingsDep` rather than a bare `Settings`: FastAPI reads a dependency's own signature, and
    an un-annotated pydantic model there is taken for a second request body.
    """
    from app.features.billing.checkout import build_checkout

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
    referral_code: str | None,
    checkout: CheckoutSessions,
    settings: Settings,
    now: datetime,
    idempotency_key: str | None = None,
) -> str:
    """Send this person to pay for a plan, and return where to send them.

    The client names a plan code, never a price or an amount: the plan row owns the price and
    Stripe is told which one to use.

    With a referral code, as in b2c, the plan is swapped for its 10%-off twin
    (`domain.referral_plan_code`) and the code travels with the checkout, so the webhook can
    credit its owner once the money arrives. A code that is unknown or the buyer's own is
    refused before Stripe is called.

    A plan is sold only for an exam this person is on: the one they signed up for, or one they
    hold. Their exam is chosen at sign-up and moving them is a support action, so an SCA account
    buying PLAB would pay for a library its every screen hides. Somebody with no exam at all may
    buy any plan, and what they buy becomes their exam.

    Nothing is granted here and no payment is recorded. Access arrives when the webhook says the
    money did: a customer who abandons the Stripe page has started a checkout and bought nothing.
    """
    plan = await repository.plan_by_code(session, plan_code)
    # A discounted plan is reached only through a code. Naming it directly
    # would be 10% off for anyone who read the plan list.
    if plan is None or domain.is_referral_plan(plan.code):
        raise errors.PlanNotAvailable()

    access = await service_access.exam_access_for(session, user_id, now=now)
    if access.codes and plan.exam_code not in access.codes:
        raise errors.PlanNotAvailable(details={"reason": "not_your_exam"})

    # The same plan again while one is running stays refused: it would buy access they have. A
    # different plan is allowed, and settlement starts it where the running access ends.
    running = {
        grant.id for grant in await entitlements.running_purchases(session, user_id, plan.exam_code, now=now)
    }
    for payment in await repository.payments_for_user(session, user_id):
        if payment.entitlement_id not in running or payment.plan_id is None:
            continue
        held_plan = await repository.plan_by_id(session, payment.plan_id)
        if held_plan is not None and domain.base_plan_code(held_plan.code) == plan.code:
            raise errors.AlreadyPurchased()

    checked_referral_code: str | None = None
    if referral_code and referral_code.strip():
        checked_referral_code = await growth.check_code_for_purchase(
            session, code=referral_code, buyer_user_id=user_id
        )
        discounted_plan = await repository.plan_by_code(session, domain.referral_plan_code(plan.code))
        if discounted_plan is None:
            raise errors.ReferralDiscountUnavailable()
        plan = discounted_plan

    base = settings.frontend_url.rstrip("/")
    try:
        return await checkout.create(
            price_id=plan.stripe_price_id,
            customer_email=email,
            success_url=f"{base}/billing/complete?session_id={{CHECKOUT_SESSION_ID}}",
            # The `?cancelled=1` marker is the only thing that separates "came
            # back from Stripe having changed their mind" from "typed /pricing",
            # because Stripe sends a cancel to this URL verbatim. Without it the
            # web cannot tell the two apart and shows every visitor the
            # "Checkout cancelled" card.
            cancel_url=f"{base}/pricing?cancelled=1",
            client_reference=str(user_id),
            referral_code=checked_referral_code,
            # Scoped to the buyer, so one person's key can never collide with another's.
            idempotency_key=f"checkout:{user_id}:{idempotency_key}" if idempotency_key else None,
        )
    except CheckoutUnavailable as exc:
        # The processor's own words go to the log, never to the customer.
        log.warning("checkout could not be started", plan=plan.code, error=str(exc))
        raise errors.CheckoutFailed() from exc
