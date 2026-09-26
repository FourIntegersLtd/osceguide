from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import InvalidInput, Unauthenticated, error_responses
from app.core.openapi import DOCUMENT_MEDIA_TYPE
from app.core.pagination import Page
from app.core.ports import CheckoutSessions, ClockDep
from app.core.settings import SettingsDep
from app.features.billing import errors, schemas, service, service_checkout, service_receipts

router = APIRouter(tags=["billing"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/billing/plans",
    response_model=Page[schemas.PlanRead],
    # Public and read-only, so the only failure is a malformed request.
    responses=error_responses(InvalidInput),
)
async def list_plans(session: Session) -> Page[schemas.PlanRead]:
    """List the plans currently on sale."""
    plans = [schemas.PlanRead(**plan_data) for plan_data in await service.list_plans(session)]
    return Page(items=plans, next_cursor=None)


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
    """Apply one Stripe webhook delivery, at most once, and only if Stripe sent it."""
    # The raw body is what the signature covers, so it is read and verified before being
    # parsed — a parsed body parameter would hand FastAPI the bytes first.
    raw = await request.body()
    event = service.verified_event(
        raw,
        request.headers.get("Stripe-Signature", ""),
        secret=settings.stripe_webhook_secret,
        now=int(clock.now().timestamp()),
    )
    outcome = await service.handle_event(session, event=event, now=clock.now())
    return schemas.WebhookResult(**outcome)


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
    """One receipt, rendered. Scoped to the caller."""
    return await service_receipts.read_receipt(session, principal.user_id, receipt_id)


@router.get(
    "/me/receipts/{receipt_id}/document",
    response_class=HTMLResponse,
    responses={
        **error_responses(Unauthenticated, errors.ReceiptNotFound),
        # Declared, not inferred: this is a document, so the generated client
        # must know it hands back markup rather than an object to parse.
        200: {"content": {DOCUMENT_MEDIA_TYPE: {}}, "description": "The receipt, as HTML."},
    },
)
async def read_receipt_document(
    receipt_id: str, principal: CurrentPrincipal, session: Session
) -> HTMLResponse:
    """The receipt as something to print, keep or send to an accountant."""
    # Served inline rather than as a download: a browser can print it to PDF, and a
    # Content-Disposition: attachment would stop somebody simply looking at it.
    html = await service_receipts.read_receipt_document(session, principal.user_id, receipt_id)
    return HTMLResponse(content=html)


@router.post(
    "/billing/checkout",
    response_model=schemas.CheckoutStarted,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Unauthenticated, errors.PlanNotAvailable, errors.CheckoutFailed),
)
async def start_checkout(
    body: schemas.StartCheckout,
    principal: CurrentPrincipal,
    session: Session,
    settings: SettingsDep,
    checkout: Annotated[CheckoutSessions, Depends(service_checkout.get_checkout)],
) -> schemas.CheckoutStarted:
    """Begin paying for a plan. The client names a plan code, never a price or an amount."""
    url = await service_checkout.start_checkout(
        session,
        user_id=principal.user_id,
        email=principal.email,
        plan_code=body.plan_code,
        checkout=checkout,
        settings=settings,
    )
    return schemas.CheckoutStarted(checkout_url=url)
