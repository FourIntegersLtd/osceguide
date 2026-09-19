"""The platform console's view of billing. Every route is `PlatformAdmin`.

`router.py` is what a customer and Stripe call. These are what the people
who answer "I paid and nothing happened" call, and they read across every
customer at once.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import Forbidden, error_responses
from app.core.pagination import CursorParams, Page
from app.core.tenancy import PlatformAdmin
from app.features.billing import errors, schemas, service_platform

router = APIRouter(tags=["billing"])

Session = Annotated[AsyncSession, Depends(get_session)]


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
    items, next_cursor = await service_platform.list_events(
        session, failed_only=failed_only, limit=page.limit, cursor=page.cursor
    )
    return Page(items=items, next_cursor=next_cursor)
