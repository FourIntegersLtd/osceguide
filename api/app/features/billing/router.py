from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import InvalidInput, error_responses
from app.core.pagination import Page
from app.core.ports import ClockDep
from app.core.settings import SettingsDep
from app.features.billing import errors, schemas, service

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
