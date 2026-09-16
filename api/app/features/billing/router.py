from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import InvalidInput, error_responses
from app.core.pagination import Page
from app.core.ports import ClockDep
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
    responses=error_responses(errors.InvalidWebhook, errors.InvalidSignature, errors.UnknownPlanError),
)
async def stripe_webhook(event: dict[str, Any], session: Session, clock: ClockDep) -> schemas.WebhookResult:
    """Apply one delivery, at most once.

    Signature verification belongs in front of this and is not yet wired; see
    docs/OPEN-QUESTIONS.md. The idempotency ledger is here regardless, because
    Stripe retries until it gets a 2xx and b2c has no record of what it applied.
    """
    result = await service.handle_event(session, event=event, now=clock.now())
    return schemas.WebhookResult(**result)
