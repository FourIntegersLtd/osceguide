from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import InvalidInput, Unauthenticated, error_responses
from app.core.pagination import Page
from app.core.ports import ClockDep
from app.core.settings import SettingsDep
from app.features.billing import errors, schemas, service, service_receipts

router = APIRouter(tags=["billing"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/billing/plans",
    response_model=Page[schemas.PlanRead],
    # Public and read-only, so the only failure is a malformed request.
    responses=error_responses(InvalidInput),
)
async def list_plans(session: Session) -> Page[schemas.PlanRead]:
    """Public: the pricing page reads this rather than hardcoding amounts, which
    is how b2c's client and server came to disagree about what a plan costs."""
    items = [schemas.PlanRead(**p) for p in await service.list_plans(session)]
    return Page(items=items, next_cursor=None)


@router.post(
    "/billing/webhooks/stripe",
    response_model=schemas.WebhookResult,
    responses=error_responses(
        errors.InvalidWebhook,
        errors.InvalidSignature,
        errors.UnknownPlanError,
        errors.UnknownExamError,
    ),
)
async def stripe_webhook(
    request: Request,
    session: Session,
    settings: SettingsDep,
    clock: ClockDep,
) -> schemas.WebhookResult:
    """Apply one delivery, at most once, and only if Stripe sent it.

    The **raw body** is what the signature covers, so it is read and verified
    before being parsed. Declaring a parsed body parameter instead would hand
    FastAPI the bytes first and leave the signature checking something else.
    """
    raw = await request.body()
    event = service.verified_event(
        raw,
        request.headers.get("Stripe-Signature", ""),
        secret=settings.stripe_webhook_secret,
        now=int(clock.now().timestamp()),
    )
    result = await service.handle_event(session, event=event, now=clock.now())
    return schemas.WebhookResult(**result)


@router.get(
    "/me/receipts",
    response_model=Page[str],
    responses=error_responses(Unauthenticated),
)
async def list_my_receipts(principal: CurrentPrincipal, session: Session) -> Page[str]:
    """The receipt ids for this person's payments, newest first."""
    return Page(items=await service_receipts.list_my_receipts(session, principal.user_id), next_cursor=None)


@router.get(
    "/me/receipts/{receipt_id}",
    response_model=schemas.ReceiptRead,
    responses=error_responses(Unauthenticated, errors.ReceiptNotFound),
)
async def read_receipt(receipt_id: str, principal: CurrentPrincipal, session: Session) -> schemas.ReceiptRead:
    """One receipt, rendered.

    Scoped to the caller. A receipt id is short and printed on a document that
    gets forwarded to an accountant or an employer, so it must not be a key
    anybody holding it can read.
    """
    return await service_receipts.read_receipt(session, principal.user_id, receipt_id)
