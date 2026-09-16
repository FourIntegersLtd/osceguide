from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import InvalidInput, Unauthenticated, error_responses
from app.features.growth import errors, schemas, service

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
