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

# The random part of a redemption's own code, and the column's width.
REDEMPTION_SUFFIX_BYTES = 3
REFERRAL_CODE_MAX_LENGTH = 32


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


async def check_code_for_purchase(session: AsyncSession, *, code: str, buyer_user_id: uuid.UUID) -> str:
    """Confirm a code may discount this person's purchase, and return it normalised.

    Called by billing before a discounted checkout starts. As in b2c, a code is reusable:
    anybody but its owner may buy with it, as often as they buy. Refused as `ReferralNotFound`
    when no shareable code matches or the code is the buyer's own.
    """
    shared = await repository.shareable_code(session, code)
    if shared is None or shared.referrer_user_id == buyer_user_id:
        # Referring yourself is not a referral, and saying "that is your own
        # code" would confirm to a guesser that the code exists.
        raise errors.ReferralNotFound()
    return shared.code


async def credit_referral_purchase(
    session: AsyncSession,
    *,
    code: str,
    referred_user_id: uuid.UUID,
    plan_duration_days: int,
    now: datetime,
) -> bool:
    """Credit the owner of `code` for a purchase that has just been paid for.

    Called by billing's webhook in the payment's own transaction, so a credit exists exactly
    when the payment does. Returns False, and credits nobody, if the code no longer resolves or
    is the buyer's own. That is logged rather than raised: the customer has paid, and a
    referral problem must never stop them getting what they bought.
    """
    shared = await repository.shareable_code(session, code)
    if shared is None or shared.referrer_user_id == referred_user_id:
        log.warning("a paid referral checkout named a code that no longer credits anyone", code=code)
        return False
    # The shared code plus a random suffix: `referrals.code` is unique, and the
    # suffix keeps the redemption readable next to the code it came from.
    redemption_suffix = secrets.token_hex(REDEMPTION_SUFFIX_BYTES).upper()
    await repository.record_redemption(
        session,
        referrer_user_id=shared.referrer_user_id,
        redemption_code=f"{shared.code}-{redemption_suffix}"[:REFERRAL_CODE_MAX_LENGTH],
        referred_user_id=referred_user_id,
        earned_pence=domain.referral_reward_pence(plan_duration_days),
        at=now,
    )
    return True


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
