"""Attributing arrivals, and reporting to partners."""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.features.billing import service as billing
from app.features.catalog import service as catalog
from app.features.growth import domain, errors, repository
from app.features.growth.schemas import (
    AcquisitionRead,
    ArrivalRecorded,
    FunnelRead,
    ReferralRead,
    TrackingReference,
)

log = get_logger(__name__)

REFERRAL_CODE_BYTES = 4

# What a referrer earns when somebody redeems their code. A constant rather
# than a database value: it is the same for everyone, so changing it is a
# deploy, not a data change.
REFERRAL_REWARD_PENCE = 500


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
    # Which exams are in the pilot is a flag on the exam row, so this asks.
    pilot_exams = await catalog.pilot_exam_codes(session)
    exam_code = None
    parsed = domain.parse_ref_id(ref_id or "", pilot_exams=pilot_exams)
    if parsed:
        _, exam_code = parsed
    elif landing_path:
        exam_code = domain.exam_from_landing_path(landing_path, pilot_exams=pilot_exams)

    arrival = await repository.record_arrival(
        session,
        partner=partner_key,
        exam_code=exam_code,
        visitor_key=visitor_key,
        ref_id=ref_id,
        landing_path=landing_path,
        utm=utm or None,
    )
    return ArrivalRecorded(id=arrival.id, partner=arrival.partner, exam_code=arrival.exam_code)


async def attribute_signup(
    session: AsyncSession, *, user_id: uuid.UUID, visitor_key: str | None, now: datetime
) -> AcquisitionRead | None:
    """Credit a signup to the partner who sent them, once.

    Returns None when there is nothing to credit — no arrival, an arrival
    outside the window, or a user already attributed.
    """
    if not visitor_key:
        return None
    arrival = await repository.latest_arrival_for_visitor(session, visitor_key)
    if arrival is None:
        return None
    if not domain.attributes(arrived_at=arrival.landed_at, signed_up_at=now):
        return None

    acquisition = await repository.record_acquisition(
        session,
        user_id=user_id,
        partner=arrival.partner,
        exam_code=arrival.exam_code,
        arrival_id=arrival.id,
        at=now,
    )
    if acquisition is None:
        return None
    return AcquisitionRead(
        partner=acquisition.partner, exam_code=acquisition.exam_code, acquired_at=acquisition.acquired_at
    )


async def ensure_reporter(
    session: AsyncSession, *, partner: str, email: str, is_platform_admin: bool
) -> None:
    """Reporting access is per partner, checked against the partner in the path
    rather than "is a reporter at all"."""
    if is_platform_admin:
        return
    if not await repository.is_reporter(session, partner=partner, email=email):
        raise errors.NotAReporter()


async def _purchases_for(session: AsyncSession, partner: str) -> int:
    """How many of a partner's people have paid."""
    user_ids = await repository.acquired_user_ids(session, partner)
    return await billing.count_payments_for_users(session, user_ids) if user_ids else 0


async def read_funnel(session: AsyncSession, *, partner: str) -> FunnelRead:
    """This partner's arrivals, signups and purchases, with the two conversion rates."""
    partner_key = (partner or "").strip().lower()
    if partner_key not in domain.PILOT_PARTNERS:
        raise errors.UnknownPartnerError()
    arrivals, signups = await repository.counts_for_partner(session, partner_key)
    purchases = await _purchases_for(session, partner_key)
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
    unredeemed = next((referral for referral in existing if referral.redeemed_at is None), None)
    if unredeemed is not None:
        return _referral_read(unredeemed.code, existing)

    code = secrets.token_hex(REFERRAL_CODE_BYTES).upper()
    referral = await repository.create_referral(session, referrer_user_id=user_id, code=code)
    return _referral_read(referral.code, [*existing, referral])


async def read_my_referrals(session: AsyncSession, user_id: uuid.UUID) -> ReferralRead:
    """This person's own referral code and what it has earned so far."""
    referrals = await repository.referrals_for(session, user_id)
    code = next((referral.code for referral in referrals if referral.redeemed_at is None), "")
    return _referral_read(code, referrals)


async def redeem_code(
    session: AsyncSession,
    *,
    code: str,
    referred_user_id: uuid.UUID,
    now: datetime,
    earned_pence: int = REFERRAL_REWARD_PENCE,
) -> ReferralRead:
    """Redeem a code for the person who was referred, crediting the referrer.

    Refused if the code does not exist, names the person redeeming it, or has
    already been used.
    """
    referral = await repository.referral_by_code(session, code)
    if referral is None:
        raise errors.ReferralNotFound()
    if referral.referrer_user_id == referred_user_id:
        # Referring yourself is not a referral.
        raise errors.ReferralNotFound()
    if referral.redeemed_at is not None:
        raise errors.ReferralAlreadyRedeemed()
    await repository.redeem(
        session, referral.id, referred_user_id=referred_user_id, earned_pence=earned_pence, at=now
    )
    referrals = await repository.referrals_for(session, referral.referrer_user_id)
    return _referral_read("", referrals)


def _referral_read(code: str, referrals: list) -> ReferralRead:  # type: ignore[type-arg]
    """Shape one person's live code plus their totals across all their referrals."""
    redeemed = [referral for referral in referrals if referral.redeemed_at is not None]
    return ReferralRead(
        code=code,
        redeemed_count=len(redeemed),
        earned_pence=sum(referral.earned_pence for referral in redeemed),
    )


async def add_reporter(session: AsyncSession, *, partner: str, email: str) -> None:
    """Give somebody reporting access to one partner's numbers."""
    partner_key = (partner or "").strip().lower()
    if partner_key not in domain.PILOT_PARTNERS:
        raise errors.UnknownPartnerError()
    await repository.add_reporter(session, partner=partner_key, email=email.strip().lower())


async def tracking_references(
    session: AsyncSession, *, partner: str, email: str, is_platform_admin: bool
) -> list[TrackingReference]:
    """The references a partner puts in its links, one per exam in the pilot.

    The other half of `parse_ref_id`. Saves a partner from typing a reference
    by hand, where a typo would silently attribute their traffic to nobody.
    """
    partner_key = (partner or "").strip().lower()
    if partner_key not in domain.PILOT_PARTNERS:
        raise errors.UnknownPartnerError()
    await ensure_reporter(session, partner=partner_key, email=email, is_platform_admin=is_platform_admin)
    pilot_exams = sorted(await catalog.pilot_exam_codes(session))
    return [
        TrackingReference(
            exam_code=exam_code,
            ref_id=domain.format_ref_id(partner_key, exam_code, pilot_exams=pilot_exams),
            landing_path=domain.landing_path_for(exam_code),
        )
        for exam_code in pilot_exams
    ]
