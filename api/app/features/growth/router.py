from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import Forbidden, InvalidInput, Unauthenticated, error_responses
from app.core.pagination import CursorParams, Page
from app.core.ports import ClockDep
from app.core.tenancy import PlatformAdmin
from app.features.growth import errors, schemas, service, service_payouts

router = APIRouter(tags=["growth"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.post(
    "/growth/arrivals",
    response_model=schemas.ArrivalRecorded,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(InvalidInput, errors.UnknownPartnerError),
)
async def record_arrival(body: schemas.RecordArrival, session: Session) -> schemas.ArrivalRecorded:
    """Public: a visitor arriving from a partner link, before any account exists.

    Unauthenticated by necessity — there is nobody to authenticate yet — which
    is why the partner must be a known one and the visitor key is opaque.
    """
    return await service.record_arrival(
        session,
        partner=body.partner,
        visitor_key=body.visitor_key,
        ref_id=body.ref_id,
        landing_path=body.landing_path,
        utm=body.utm,
    )


@router.get(
    "/growth/partners/{partner}/funnel",
    response_model=schemas.FunnelRead,
    responses=error_responses(Unauthenticated, errors.NotAReporter, errors.UnknownPartnerError),
)
async def read_funnel(partner: str, principal: CurrentPrincipal, session: Session) -> schemas.FunnelRead:
    """Checked against the partner in the path, so one partner's reporter
    cannot read another's numbers."""
    await service.ensure_reporter(
        session,
        partner=partner.strip().lower(),
        email=principal.email,
        is_platform_admin=principal.is_platform_admin,
    )
    return await service.read_funnel(session, partner=partner)


@router.post(
    "/growth/acquisitions",
    response_model=schemas.AcquisitionRead | None,
    responses=error_responses(Unauthenticated),
)
async def credit_signup(
    body: schemas.CreditSignup, principal: CurrentPrincipal, session: Session, clock: ClockDep
) -> schemas.AcquisitionRead | None:
    """Credit this new account to whoever sent them, once.

    Its own route rather than a step inside registering: `growth` sits above
    `identity`, so registration cannot call it, and a partner who sent somebody
    was credited with nothing at all until this existed. Null when there is
    nothing to credit, which is the ordinary case.
    """
    return await service.attribute_signup(
        session, user_id=principal.user_id, visitor_key=body.visitor_key, now=clock.now()
    )


@router.get(
    "/growth/partners/{partner}/ref-ids",
    response_model=Page[schemas.TrackingReference],
    responses=error_responses(Unauthenticated, errors.NotAReporter, errors.UnknownPartnerError),
)
async def read_tracking_references(
    partner: str, principal: CurrentPrincipal, session: Session
) -> Page[schemas.TrackingReference]:
    """The references this partner puts in its links, one per exam in the pilot.

    Reporter-gated like the funnel: a reference is commercially meaningful, and
    one partner has no business reading another's.
    """
    items = await service.tracking_references(
        session,
        partner=partner,
        email=principal.email,
        is_platform_admin=principal.is_platform_admin,
    )
    return Page(items=items, next_cursor=None)


@router.post(
    "/growth/partners/{partner}/reporters",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(Forbidden, errors.UnknownPartnerError),
)
async def add_reporter(
    partner: str, body: schemas.AddReporter, admin: PlatformAdmin, session: Session
) -> Response:
    """Platform admin only: partners do not appoint their own reporters."""
    _ = admin
    await service.add_reporter(session, partner=partner, email=body.email)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/me/referrals/redeem",
    response_model=schemas.ReferralRead,
    responses=error_responses(Unauthenticated, errors.ReferralNotFound, errors.ReferralAlreadyRedeemed),
)
async def redeem_referral(
    body: schemas.RedeemReferral, principal: CurrentPrincipal, session: Session, clock: ClockDep
) -> schemas.ReferralRead:
    """Codes could be issued and never redeemed, so a referrer earned nothing."""
    return await service.redeem_code(
        session, code=body.code, referred_user_id=principal.user_id, now=clock.now()
    )


@router.post(
    "/me/referral-code",
    response_model=schemas.ReferralRead,
    responses=error_responses(Unauthenticated),
)
async def issue_code(principal: CurrentPrincipal, session: Session) -> schemas.ReferralRead:
    """One code per person; asking again returns the one they have."""
    return await service.issue_code(session, user_id=principal.user_id)


@router.get(
    "/me/referrals",
    response_model=schemas.ReferralRead,
    responses=error_responses(Unauthenticated),
)
async def read_my_referrals(principal: CurrentPrincipal, session: Session) -> schemas.ReferralRead:
    return await service.read_my_referrals(session, principal.user_id)


@router.get(
    "/growth/referrals",
    response_model=Page[schemas.ReferralAdminRead],
    responses=error_responses(Forbidden),
)
async def list_referrals(
    admin: PlatformAdmin,
    session: Session,
    page: Annotated[CursorParams, Depends()],
    payout_status: str | None = None,
) -> Page[schemas.ReferralAdminRead]:
    """The settlement queue: redeemed referrals, and whether each has been paid.

    Platform admin only, and deliberately not a partner's or a referrer's
    view — it names both sides of every referral and what is owed on it.
    """
    _ = admin
    items, next_cursor = await service_payouts.list_redeemed_referrals(
        session, limit=page.limit, cursor=page.cursor, payout_status=payout_status
    )
    return Page(items=items, next_cursor=next_cursor)


@router.post(
    "/growth/referrals/{referral_id}/payout",
    response_model=schemas.ReferralAdminRead,
    responses=error_responses(Forbidden, errors.ReferralNotFound, errors.ReferralNotRedeemed),
)
async def set_referral_payout(
    referral_id: uuid.UUID,
    body: schemas.SetReferralPayout,
    admin: PlatformAdmin,
    session: Session,
    clock: ClockDep,
) -> schemas.ReferralAdminRead:
    """Record a settlement made outside the product.

    Nothing here moves money. It writes down that somebody did, who said so
    and when, which is the whole of what the retiring app's `payout_status`
    flag meant and rather more than it recorded.
    """
    return await service_payouts.set_referral_payout(
        session,
        referral_id,
        payout_status=body.payout_status,
        payout_reference=body.payout_reference,
        actor_user_id=admin.user_id,
        now=clock.now(),
    )
