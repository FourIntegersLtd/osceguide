"""Staff pricing: what the platform sells, created and retired from the console.

A plan never changes once written: its price id is on every payment that bought it. A new price
is a new plan with a new code, and the old one is taken off sale. Each plan is written with its
10%-off referral twin (`domain.referral_plan_code`), and the two go on and off sale together.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.core.ports import CheckoutSessions, CheckoutUnavailable
from app.core.settings import SettingsDep
from app.features.billing import domain, errors, repository
from app.features.billing.models import Plan
from app.features.billing.schemas import CreatePlan, PlatformPlanRead
from app.features.catalog import service as catalog
from app.features.catalog.errors import UnknownExamError as CatalogUnknownExam
from app.features.tenancy import service_audit


def get_stripe_prices(settings: SettingsDep) -> CheckoutSessions:
    """The Stripe adapter for pricing, as the router's dependency. Overridden in tests.

    Its own dependency rather than `service_checkout.get_checkout`, so a deployment with no
    Stripe key answers `price_creation_failed` here, not a customer's `checkout_failed`.
    """
    from app.features.billing.checkout import build_checkout  # noqa: PLC0415

    try:
        return build_checkout(settings)
    except CheckoutUnavailable as exc:
        raise errors.PriceCreationFailed() from exc


async def list_plans(session: AsyncSession) -> list[PlatformPlanRead]:
    """Every full-price plan, on sale or retired, each with its referral twin's price."""
    plans = await repository.all_plans(session)
    referral_prices = {plan.code: plan.amount_pence for plan in plans if domain.is_referral_plan(plan.code)}
    return [
        _read(plan, referral_prices.get(domain.referral_plan_code(plan.code)))
        for plan in plans
        if not domain.is_referral_plan(plan.code)
    ]


async def create_plan(
    session: AsyncSession, body: CreatePlan, *, checkout: CheckoutSessions, actor: Principal
) -> PlatformPlanRead:
    """Price a published platform exam: two Stripe prices, then the plan and its referral twin.

    Stripe is called before anything is written, so a refusal leaves no plan that cannot be
    bought. A second-price failure leaves one unused Stripe price behind, which costs nothing.
    """
    code = body.code
    twin_code = domain.referral_plan_code(code)
    if domain.is_referral_plan(code):
        raise errors.PlanCodeTaken("A plan code may not end in _referral; that is its discount's code.")
    for taken in (code, twin_code):
        if await repository.any_plan_by_code(session, taken) is not None:
            raise errors.PlanCodeTaken(f"A plan already has the code {taken!r}.")

    try:
        # The platform catalogue only (no org): an institution's exam is not sold to consumers.
        exam = await catalog.resolve_exam(session, body.exam_code)
    except CatalogUnknownExam as exc:
        raise errors.UnknownExamError(f"{exc} Only a published platform exam can be priced.") from exc

    twin_amount = domain.referral_amount_pence(body.amount_pence)
    product_name = f"{exam.name} · {body.duration_days} days"
    try:
        price_id = await checkout.create_price(
            amount_pence=body.amount_pence, currency="gbp", product_name=product_name, plan_code=code
        )
        twin_price_id = await checkout.create_price(
            amount_pence=twin_amount,
            currency="gbp",
            product_name=f"{product_name} (referral)",
            plan_code=twin_code,
        )
    except CheckoutUnavailable as exc:
        raise errors.PriceCreationFailed() from exc

    try:
        plan = await repository.create_plan(
            session,
            code=code,
            stripe_price_id=price_id,
            amount_pence=body.amount_pence,
            duration_days=body.duration_days,
            exam_code=exam.code,
        )
        await repository.create_plan(
            session,
            code=twin_code,
            stripe_price_id=twin_price_id,
            amount_pence=twin_amount,
            duration_days=body.duration_days,
            exam_code=exam.code,
        )
    except IntegrityError as exc:
        # Two staff creating the same code at once: the check above passed for both.
        raise errors.PlanCodeTaken(f"A plan already has the code {code!r}.") from exc
    await service_audit.record(
        session,
        actor=actor,
        action="billing.plan_created",
        target_type="plan",
        target_id=code,
        summary=f"{exam.code} · £{body.amount_pence / 100:.2f} for {body.duration_days} days",
        meta={"price_id": price_id, "referral_price_id": twin_price_id},
    )
    return _read(plan, twin_amount)


async def set_plan_active(
    session: AsyncSession, code: str, *, active: bool, actor: Principal, now: datetime
) -> PlatformPlanRead:
    """Put a plan and its referral twin on sale or take them off it.

    Retiring stops new checkouts only: a payment already under way is still granted, because the
    webhook resolves prices across every plan (`service.handle_event`).
    """
    plan = await repository.any_plan_by_code(session, code)
    if plan is None or domain.is_referral_plan(code):
        raise errors.PlanNotFound()
    if active:
        # Only what settlement can grant goes back on sale: a legacy row with no exam, or one
        # whose exam is no longer published, would charge a card and grant nothing.
        try:
            await catalog.resolve_exam(session, plan.exam_code)
        except CatalogUnknownExam as exc:
            raise errors.UnknownExamError(
                f"{exc} A plan goes back on sale only for a published platform exam."
            ) from exc
    twin_code = domain.referral_plan_code(code)
    await repository.set_plans_active(session, [code, twin_code], active=active)
    await service_audit.record(
        session,
        actor=actor,
        action="billing.plan_put_on_sale" if active else "billing.plan_retired",
        target_type="plan",
        target_id=code,
        at=now,
    )
    await session.refresh(plan)
    twin = await repository.any_plan_by_code(session, twin_code)
    return _read(plan, twin.amount_pence if twin else None)


def _read(plan: Plan, referral_amount_pence: int | None) -> PlatformPlanRead:
    """The staff view of one plan row."""
    return PlatformPlanRead(
        code=plan.code,
        exam_code=plan.exam_code,
        amount_pence=plan.amount_pence,
        currency=plan.currency,
        duration_days=plan.duration_days,
        active=plan.active,
        stripe_price_id=plan.stripe_price_id,
        referral_amount_pence=referral_amount_pence,
        created_at=plan.created_at,
    )
