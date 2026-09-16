"""Attributing arrivals, and reporting to partners."""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.features.growth import domain, errors, repository
from app.features.growth.schemas import (
    AcquisitionRead,
    ArrivalRecorded,
    FunnelRead,
    ReferralRead,
)

log = get_logger(__name__)

REFERRAL_CODE_BYTES = 4


async def record_arrival(
    session: AsyncSession,
    *,
    partner: str,
    visitor_key: str,
    ref_id: str | None,
    landing_path: str | None,
    utm: dict[str, str],
) -> ArrivalRecorded:
    """Log a visit from a partner link, before any account exists."""
    partner_key = (partner or "").strip().lower()
    if partner_key not in domain.PILOT_PARTNERS:
        raise errors.UnknownPartnerError()

    # The exam comes from the reference if it carries one, else the path.
    exam_code = None
    parsed = domain.parse_ref_id(ref_id or "")
    if parsed:
        _, exam_code = parsed
    elif landing_path:
        exam_code = domain.exam_from_landing_path(landing_path)

    row = await repository.record_arrival(
        session,
        partner=partner_key,
        exam_code=exam_code,
        visitor_key=visitor_key,
        ref_id=ref_id,
        landing_path=landing_path,
        utm=utm or None,
    )
    return ArrivalRecorded(id=row.id, partner=row.partner, exam_code=row.exam_code)


async def attribute_signup(
    session: AsyncSession, *, user_id: uuid.UUID, visitor_key: str | None, now: datetime
) -> AcquisitionRead | None:
    """Credit a signup to the partner who sent them, once.

    Returns None when there is nothing to credit — no arrival, an arrival
    outside the window, or a user already attributed. Silence is the right
    answer: signing up without a partner is the normal case.
    """
    if not visitor_key:
        return None
    arrival = await repository.latest_arrival_for_visitor(session, visitor_key)
    if arrival is None:
        return None
    if not domain.attributes(arrived_at=arrival.landed_at, signed_up_at=now):
        return None

    row = await repository.record_acquisition(
        session,
        user_id=user_id,
        partner=arrival.partner,
        exam_code=arrival.exam_code,
        arrival_id=arrival.id,
        at=now,
    )
    if row is None:
        return None
    return AcquisitionRead(partner=row.partner, exam_code=row.exam_code, acquired_at=row.acquired_at)


async def ensure_reporter(
    session: AsyncSession, *, partner: str, email: str, is_platform_admin: bool
) -> None:
    """Reporting access is per partner.

    Checked against the partner in the path rather than "is a reporter at all",
    so one partner's reporter cannot read another's numbers.
    """
    if is_platform_admin:
        return
    if not await repository.is_reporter(session, partner=partner, email=email):
        raise errors.NotAReporter()


async def read_funnel(session: AsyncSession, *, partner: str, purchases: int = 0) -> FunnelRead:
    partner_key = (partner or "").strip().lower()
    if partner_key not in domain.PILOT_PARTNERS:
        raise errors.UnknownPartnerError()
    arrivals, signups = await repository.counts_for_partner(session, partner_key)
    funnel = domain.funnel(arrivals=arrivals, signups=signups, purchases=purchases)
    return FunnelRead(
        partner=partner_key,
        arrivals=funnel.arrivals,
        signups=funnel.signups,
        purchases=funnel.purchases,
        signup_rate=funnel.signup_rate,
        purchase_rate=funnel.purchase_rate,
    )


# --- referrals -------------------------------------------------------------


async def issue_code(session: AsyncSession, *, user_id: uuid.UUID) -> ReferralRead:
    """One code per person, reused if they already have one."""
    existing = await repository.referrals_for(session, user_id)
    unredeemed = next((r for r in existing if r.redeemed_at is None), None)
    if unredeemed is not None:
        return _referral_read(unredeemed.code, existing)

    code = secrets.token_hex(REFERRAL_CODE_BYTES).upper()
    row = await repository.create_referral(session, referrer_user_id=user_id, code=code)
    return _referral_read(row.code, [*existing, row])


async def read_my_referrals(session: AsyncSession, user_id: uuid.UUID) -> ReferralRead:
    rows = await repository.referrals_for(session, user_id)
    code = next((r.code for r in rows if r.redeemed_at is None), "")
    return _referral_read(code, rows)


async def redeem_code(
    session: AsyncSession,
    *,
    code: str,
    referred_user_id: uuid.UUID,
    earned_pence: int,
    now: datetime,
) -> None:
    row = await repository.referral_by_code(session, code)
    if row is None:
        raise errors.ReferralNotFound()
    if row.referrer_user_id == referred_user_id:
        # Referring yourself is not a referral.
        raise errors.ReferralNotFound()
    await repository.redeem(
        session, row.id, referred_user_id=referred_user_id, earned_pence=earned_pence, at=now
    )


def _referral_read(code: str, rows: list) -> ReferralRead:  # type: ignore[type-arg]
    redeemed = [r for r in rows if r.redeemed_at is not None]
    return ReferralRead(
        code=code,
        redeemed_count=len(redeemed),
        earned_pence=sum(r.earned_pence for r in redeemed),
    )
