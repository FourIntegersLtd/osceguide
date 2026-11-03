"""The platform console's view of billing. Every route is `PlatformAdmin`.

`router.py` is what a customer and Stripe call. These are what the people
who answer "I paid and nothing happened" call, and they read across every
customer at once.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.db import SessionDep as Session
from app.core.errors import Forbidden, error_responses
from app.core.pagination import CursorParams, Page
from app.core.ports import CheckoutSessions, ClockDep
from app.core.tenancy import PlatformAdmin
from app.features.billing import (
    errors,
    schemas,
    service_plans,
    service_platform,
    service_platform_actions,
)

router = APIRouter(tags=["billing"])


@router.get(
    "/platform/users/{user_id}/payments",
    response_model=Page[schemas.PlatformPaymentRead],
    responses=error_responses(Forbidden, errors.PayerNotFound),
)
async def list_user_payments_for_support(
    user_id: uuid.UUID, admin: PlatformAdmin, session: Session
) -> Page[schemas.PlatformPaymentRead]:
    """This person's payments, newest first, with what each one bought."""
    _ = admin
    return Page(items=await service_platform.payments_for_user(session, user_id), next_cursor=None)


@router.get(
    "/platform/users/{user_id}/billing-access",
    response_model=Page[schemas.PlatformExamAccessRead],
    responses=error_responses(Forbidden, errors.PayerNotFound),
)
async def read_user_access_for_support(
    user_id: uuid.UUID, admin: PlatformAdmin, session: Session, clock: ClockDep
) -> Page[schemas.PlatformExamAccessRead]:
    """Per exam: the station limit, stations sat, why (`plan:<code>`, `unlimited:<source>` or
    `no_access`) and the grants behind it."""
    _ = admin
    items = await service_platform.access_for_user(session, user_id, now=clock.now())
    return Page(items=items, next_cursor=None)


@router.get(
    "/platform/users/{user_id}/billing-events",
    response_model=Page[schemas.StripeEventRead],
    responses=error_responses(Forbidden, errors.PayerNotFound),
)
async def list_user_billing_events_for_support(
    user_id: uuid.UUID, admin: PlatformAdmin, session: Session
) -> Page[schemas.StripeEventRead]:
    """Every webhook delivery that named this person's address, applied or
    refused. A refused one with a `failure` is the "paid but no access" case."""
    _ = admin
    return Page(items=await service_platform.events_for_user(session, user_id), next_cursor=None)


@router.get(
    "/platform/billing/events",
    response_model=Page[schemas.StripeEventRead],
    responses=error_responses(Forbidden),
)
async def list_billing_events(
    admin: PlatformAdmin,
    session: Session,
    page: Annotated[CursorParams, Depends()],
    failed_only: Annotated[bool, Query(description="Only deliveries recorded but never applied")] = False,
) -> Page[schemas.StripeEventRead]:
    """The webhook ledger, newest first. With `failed_only`, the reconcile queue."""
    _ = admin
    events, next_cursor = await service_platform.list_events(
        session, failed_only=failed_only, limit=page.limit, cursor=page.cursor
    )
    return Page(items=events, next_cursor=next_cursor)


@router.post(
    "/platform/billing/events/{event_id}/replay",
    response_model=schemas.WebhookResult,
    responses=error_responses(
        Forbidden,
        errors.BillingEventNotFound,
        errors.InvalidWebhook,
        errors.UnknownPlanError,
        errors.UnknownExamError,
    ),
)
async def replay_billing_event(
    event_id: str, admin: PlatformAdmin, session: Session, clock: ClockDep
) -> schemas.WebhookResult:
    """Apply a refused delivery again, once its cause is fixed. `already_applied`
    for one that went through; the same refusal, and a new audit row, for one
    whose cause is not fixed yet."""
    outcome = await service_platform_actions.replay_event(session, event_id, actor=admin, now=clock.now())
    return schemas.WebhookResult(**outcome)


@router.post(
    "/platform/users/{user_id}/payments",
    response_model=schemas.PlatformPaymentRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        Forbidden,
        errors.PayerNotFound,
        errors.PlanNotAvailable,
        errors.PaymentAlreadyRecorded,
        errors.UnknownPlanError,
        errors.UnknownExamError,
    ),
)
async def record_manual_payment(
    user_id: uuid.UUID,
    body: schemas.RecordManualPayment,
    admin: PlatformAdmin,
    session: Session,
    clock: ClockDep,
) -> schemas.PlatformPaymentRead:
    """Record a payment that did not come through Stripe, granting what it bought."""
    return await service_platform_actions.record_manual_payment(
        session,
        user_id,
        plan_code=body.plan_code,
        intent_id=body.stripe_payment_intent_id,
        amount_total_pence=body.amount_total_pence,
        paid_at=body.paid_at,
        note=body.note,
        send_receipt=body.send_receipt,
        start=body.start,
        actor=admin,
        now=clock.now(),
    )


@router.post(
    "/platform/payments/{payment_id}/refund",
    response_model=schemas.PlatformPaymentRead,
    responses=error_responses(Forbidden, errors.PaymentNotFound),
)
async def record_refund(
    payment_id: uuid.UUID,
    body: schemas.RefundRequest,
    admin: PlatformAdmin,
    session: Session,
    clock: ClockDep,
) -> schemas.PlatformPaymentRead:
    """Withdraw what a refunded payment bought. The money moves in Stripe; the row stays."""
    return await service_platform_actions.refund(
        session, payment_id, reason=body.reason, actor=admin, now=clock.now()
    )


@router.post(
    "/platform/payments/{payment_id}/stripe-refund",
    response_model=schemas.PlatformPaymentRead,
    responses=error_responses(
        Forbidden,
        errors.PaymentNotFound,
        errors.NotAStripePayment,
        errors.StripeRefundFailed,
        errors.PaymentAlreadyRefunded,
        errors.StripeRefundRefused,
    ),
)
async def refund_in_stripe(
    payment_id: uuid.UUID,
    body: schemas.RefundRequest,
    admin: PlatformAdmin,
    session: Session,
    clock: ClockDep,
    stripe: Annotated[CheckoutSessions, Depends(service_platform_actions.get_stripe_refunds)],
) -> schemas.PlatformPaymentRead:
    """Refund the payment in Stripe, then withdraw what it bought. If Stripe refuses, nothing changes."""
    return await service_platform_actions.stripe_refund(
        session, payment_id, reason=body.reason, stripe=stripe, actor=admin, now=clock.now()
    )


@router.get(
    "/platform/billing/plans",
    response_model=Page[schemas.PlatformPlanRead],
    responses=error_responses(Forbidden),
)
async def list_platform_plans(admin: PlatformAdmin, session: Session) -> Page[schemas.PlatformPlanRead]:
    """Every plan the platform has priced, on sale or retired. A small table, so not paged."""
    _ = admin
    return Page(items=await service_plans.list_plans(session), next_cursor=None)


@router.post(
    "/platform/billing/plans",
    response_model=schemas.PlatformPlanRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        Forbidden, errors.PlanCodeTaken, errors.UnknownExamError, errors.PriceCreationFailed
    ),
)
async def create_platform_plan(
    body: schemas.CreatePlan,
    admin: PlatformAdmin,
    session: Session,
    checkout: Annotated[CheckoutSessions, Depends(service_plans.get_stripe_prices)],
) -> schemas.PlatformPlanRead:
    """Price an exam: creates the Stripe prices and the plan with its 10%-off referral twin."""
    return await service_plans.create_plan(session, body, checkout=checkout, actor=admin)


@router.patch(
    "/platform/billing/plans/{plan_code}",
    response_model=schemas.PlatformPlanRead,
    responses=error_responses(
        Forbidden, errors.PlanNotFound, errors.UnknownExamError, errors.EmptyPlanUpdate
    ),
)
# Takes a plan on or off sale, and/or sets how many stations it unlocks.
async def update_platform_plan(
    plan_code: str,
    body: schemas.UpdatePlan,
    admin: PlatformAdmin,
    session: Session,
    clock: ClockDep,
) -> schemas.PlatformPlanRead:
    """Change a plan and its referral twin: on sale or retired, and/or their station limit."""
    return await service_plans.update_plan(session, plan_code, body, actor=admin, now=clock.now())
