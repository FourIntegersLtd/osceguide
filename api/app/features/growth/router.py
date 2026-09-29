"""HTTP routes for partner attribution and referrals. Each hands straight to `service`."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import Forbidden, InvalidInput, Unauthenticated, error_responses
from app.core.pagination import CursorParams, Page
from app.core.ports import ClockDep, EventCounts
from app.core.rate_limit import USER_WRITE, TooManyRequests, per_user
from app.core.tenancy import PlatformAdmin
from app.features.growth import errors, schemas, service, service_payouts, service_spend

router = APIRouter(tags=["growth"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.post(
    "/growth/arrivals",
    response_model=schemas.ArrivalRecorded,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(InvalidInput, errors.UnknownPartnerError),
)
async def record_arrival(body: schemas.RecordArrival, session: Session) -> schemas.ArrivalRecorded:
    """Public: a visitor arriving from a partner link, before any account exists."""
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
    """A partner's funnel: arrivals, signups and purchases. Reporter-gated per partner."""
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

    Returns null when there is nothing to credit, which is the ordinary case.
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

    Reporter-gated like the funnel.
    """
    references = await service.tracking_references(
        session,
        partner=partner,
        email=principal.email,
        is_platform_admin=principal.is_platform_admin,
    )
    return Page(items=references, next_cursor=None)


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
    "/me/referral-code",
    response_model=schemas.ReferralRead,
    responses=error_responses(TooManyRequests, Unauthenticated),
    dependencies=[Depends(per_user(USER_WRITE))],
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


# The frontend does its own client-side paging (10 per page) and search over a
# single fetch, so this accepts a much larger cap than the keyset pages
# elsewhere in this router.
MAX_REFERRAL_HISTORY_LIMIT = service.MAX_REFERRAL_HISTORY_ROWS


@router.get(
    "/me/referrals/history",
    response_model=Page[schemas.ReferralHistoryRead],
    responses=error_responses(Unauthenticated),
)
async def read_my_referral_history(
    principal: CurrentPrincipal,
    session: Session,
    limit: Annotated[int, Query(ge=1, le=MAX_REFERRAL_HISTORY_LIMIT)] = MAX_REFERRAL_HISTORY_LIMIT,
) -> Page[schemas.ReferralHistoryRead]:
    """This person's own redeemed referrals: who joined, what they bought, and what it earned.

    No cursor: the frontend pages and searches this list client-side, so one
    call returns up to `limit` rows and there is nothing to page further.
    """
    rows = await service.read_my_referral_history(session, user_id=principal.user_id, limit=limit)
    return Page(items=rows, next_cursor=None)


@router.get(
    "/me/referral-payout-details",
    response_model=schemas.PayoutDetailsRead,
    responses=error_responses(Unauthenticated, errors.PayoutDetailsNotFound),
)
async def read_my_payout_details(principal: CurrentPrincipal, session: Session) -> schemas.PayoutDetailsRead:
    """This person's own bank details for referral payouts, sort code in full, account number masked."""
    return await service.read_my_payout_details(session, user_id=principal.user_id)


@router.put(
    "/me/referral-payout-details",
    response_model=schemas.PayoutDetailsRead,
    responses=error_responses(Unauthenticated, InvalidInput, errors.PayoutAccountNumberRequired),
)
async def write_my_payout_details(
    body: schemas.PayoutDetailsWrite, principal: CurrentPrincipal, session: Session
) -> schemas.PayoutDetailsRead:
    """Save or update this person's bank details for referral payouts."""
    return await service.write_my_payout_details(session, user_id=principal.user_id, body=body)


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

    Platform admin only — it names both sides of every referral and what is owed.
    """
    _ = admin
    referrals, next_cursor = await service_payouts.list_redeemed_referrals(
        session, limit=page.limit, cursor=page.cursor, payout_status=payout_status
    )
    return Page(items=referrals, next_cursor=next_cursor)


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

    Nothing here moves money — it records who said it happened, and when.
    """
    return await service_payouts.set_referral_payout(
        session,
        referral_id,
        payout_status=body.payout_status,
        payout_reference=body.payout_reference,
        actor_user_id=admin.user_id,
        now=clock.now(),
    )


# Our arrival ledger for a partner beside Mixpanel's landing count, for a date range.
@router.get(
    "/growth/partners/{partner}/reconciliation",
    response_model=schemas.LandingReconciliationRead,
    responses=error_responses(Forbidden, errors.UnknownPartnerError, errors.InvalidDateRangeError),
)
async def read_landing_reconciliation(
    partner: str,
    admin: PlatformAdmin,
    session: Session,
    event_counts: Annotated[EventCounts, Depends(service_spend.get_event_counts)],
    from_date: Annotated[date, Query(description="Inclusive UTC date")],
    to_date: Annotated[date, Query(description="Inclusive UTC date")],
    exam_code: Annotated[str | None, Query(max_length=32)] = None,
    utm_campaign: Annotated[str | None, Query(max_length=100)] = None,
) -> schemas.LandingReconciliationRead:
    _ = admin
    return await service_spend.reconcile_landings(
        session,
        partner=partner,
        from_date=from_date,
        to_date=to_date,
        exam_code=exam_code,
        utm_campaign=utm_campaign,
        event_counts=event_counts,
    )


# A partner's estimated click spend for a date range, against what the people it sent paid.
@router.get(
    "/growth/partners/{partner}/spend",
    response_model=schemas.PartnerSpendRead,
    responses=error_responses(Forbidden, errors.UnknownPartnerError, errors.InvalidDateRangeError),
)
async def read_partner_spend(
    partner: str,
    admin: PlatformAdmin,
    session: Session,
    from_date: Annotated[date, Query(description="Inclusive UTC date")],
    to_date: Annotated[date, Query(description="Inclusive UTC date")],
) -> schemas.PartnerSpendRead:
    _ = admin
    return await service_spend.read_spend(session, partner=partner, from_date=from_date, to_date=to_date)


# A partner pilot's cost per click and spend alert settings.
@router.get(
    "/growth/partners/{partner}/pilot-config",
    response_model=schemas.PilotConfigRead,
    responses=error_responses(Forbidden, errors.UnknownPartnerError),
)
async def read_pilot_config(partner: str, admin: PlatformAdmin, session: Session) -> schemas.PilotConfigRead:
    _ = admin
    return await service_spend.read_config(session, partner=partner)


# Change a partner pilot's cost per click or spend alerts.
@router.patch(
    "/growth/partners/{partner}/pilot-config",
    response_model=schemas.PilotConfigRead,
    responses=error_responses(Forbidden, errors.UnknownPartnerError),
)
async def update_pilot_config(
    partner: str, body: schemas.UpdatePilotConfig, admin: PlatformAdmin, session: Session
) -> schemas.PilotConfigRead:
    _ = admin
    return await service_spend.update_config(session, partner=partner, changes=body)
