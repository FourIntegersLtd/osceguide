"""Attributing arrivals, and reporting to partners."""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.secrets_at_rest import decrypt_text, encrypt_text
from app.core.settings import get_settings
from app.features.billing import service as billing
from app.features.catalog import service as catalog
from app.features.growth import domain, errors, repository
from app.features.growth.schemas import (
    AcquisitionRead,
    ArrivalRecorded,
    FunnelRead,
    PayoutDetailsRead,
    PayoutDetailsWrite,
    ReferralHistoryRead,
    ReferralRead,
    TrackingReference,
)
from app.features.identity import service as identity

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
    plan_code: str | None = None,
) -> bool:
    """Credit the owner of `code` for a purchase that has just been paid for.

    Called by billing's webhook in the payment's own transaction, so a credit exists exactly
    when the payment does. Returns False, and credits nobody, if the code no longer resolves or
    is the buyer's own. That is logged rather than raised: the customer has paid, and a
    referral problem must never stop them getting what they bought. `plan_code` is stored on
    the redeemed row so the referrer's own history can name what was bought.
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
        plan_code=plan_code,
    )
    return True


# --- A1: a referrer's own bank details for payouts --------------------------

# How many digits of a stored account number are shown back to the person who
# owns it. Matches the retiring client's `blurAccountNumber`.
ACCOUNT_NUMBER_VISIBLE_DIGITS = 4


async def read_my_payout_details(session: AsyncSession, *, user_id: uuid.UUID) -> PayoutDetailsRead:
    """This person's own bank details, sort code in full and account number masked.

    Raises `PayoutDetailsNotFound` when nothing has ever been saved — the
    router turns that into a 404 the settings screen reads as "nothing on
    file yet" rather than an error.
    """
    stored = await repository.payout_details_by_user(session, user_id)
    if stored is None:
        raise errors.PayoutDetailsNotFound()
    account_number = decrypt_text(stored.account_number_ciphertext, key=get_settings().payout_details_key)
    return PayoutDetailsRead(
        bank_name=stored.bank_name,
        account_holder_name=stored.account_holder_name,
        sort_code=domain.format_sort_code(
            decrypt_text(stored.sort_code_ciphertext, key=get_settings().payout_details_key)
        ),
        account_number_last4=account_number[-ACCOUNT_NUMBER_VISIBLE_DIGITS:],
        updated_at=stored.updated_at,
    )


async def write_my_payout_details(
    session: AsyncSession, *, user_id: uuid.UUID, body: PayoutDetailsWrite
) -> PayoutDetailsRead:
    """Save this person's bank details, encrypting the sort code and account number.

    `account_number` may be omitted on an update, keeping whatever is already
    stored — so changing a bank's name does not force retyping a number that
    never left the client the first time. Omitting it with nothing stored yet
    is refused as `PayoutAccountNumberRequired`.
    """
    existing = await repository.payout_details_by_user(session, user_id)
    if body.account_number is not None:
        account_number = domain.validate_account_number(body.account_number)
    elif existing is not None:
        account_number = decrypt_text(
            existing.account_number_ciphertext, key=get_settings().payout_details_key
        )
    else:
        raise errors.PayoutAccountNumberRequired()
    sort_code_digits = domain.normalise_sort_code(body.sort_code)
    stored = await repository.upsert_payout_details(
        session,
        user_id=user_id,
        bank_name=body.bank_name.strip(),
        account_holder_name=body.account_holder_name.strip(),
        sort_code_ciphertext=encrypt_text(sort_code_digits, key=get_settings().payout_details_key),
        account_number_ciphertext=encrypt_text(account_number, key=get_settings().payout_details_key),
    )
    return PayoutDetailsRead(
        bank_name=stored.bank_name,
        account_holder_name=stored.account_holder_name,
        sort_code=domain.format_sort_code(sort_code_digits),
        account_number_last4=account_number[-ACCOUNT_NUMBER_VISIBLE_DIGITS:],
        updated_at=stored.updated_at,
    )


# --- A2: a referrer's own referral history -----------------------------------

# The frontend pages through this client-side (10 per page, searching by
# email) rather than asking the server again, so it fetches up to this many
# rows in one call instead of the usual keyset page size.
MAX_REFERRAL_HISTORY_ROWS = 500


async def read_my_referral_history(
    session: AsyncSession, *, user_id: uuid.UUID, limit: int
) -> list[ReferralHistoryRead]:
    """This person's own redeemed referrals, newest first, with who joined and what they bought.

    Referee emails are resolved in one lookup rather than per row.
    """
    bounded_limit = min(limit, MAX_REFERRAL_HISTORY_ROWS)
    redeemed = await repository.my_redeemed_referrals_page(
        session, referrer_user_id=user_id, limit=bounded_limit
    )
    referee_ids = [referral.referred_user_id for referral in redeemed if referral.referred_user_id]
    referees = await identity.user_refs_by_ids(session, referee_ids)
    rows: list[ReferralHistoryRead] = []
    for referral in redeemed:
        referee = referees.get(referral.referred_user_id) if referral.referred_user_id else None
        rows.append(
            ReferralHistoryRead(
                id=referral.id,
                code=referral.code,
                referee_email=referee.email if referee else "",
                # Not None: `redeemed` only contains rows where it is set.
                redeemed_at=referral.redeemed_at,
                plan_code=referral.plan_code,
                plan_label=billing.plan_label(referral.plan_code) if referral.plan_code else None,
                earned_pence=referral.earned_pence,
                payout_status=referral.payout_status,
                paid_at=referral.paid_at,
            )
        )
    return rows


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
