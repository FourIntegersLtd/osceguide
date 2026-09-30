"""Referral payouts: what is owed, and whether it has been settled.

Nothing here moves money — referrals are paid by a bank transfer made outside
the product. This is only the record of whether that happened, who says so,
and against which transfer reference.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.secrets_at_rest import decrypt_text
from app.core.settings import get_settings
from app.features.growth import domain, errors, repository
from app.features.growth.models import ReferralPayoutDetails
from app.features.growth.schemas import PayoutDetailsAdminRead, ReferralAdminRead
from app.features.identity import service as identity


def _admin_payout_details(stored: ReferralPayoutDetails | None) -> PayoutDetailsAdminRead | None:
    """Decrypt one referrer's stored bank details for platform admin settlement.

    `None` when nothing was ever saved, which the settlement queue reads as
    "pay this the way it was paid before this existed."
    """
    if stored is None:
        return None
    return PayoutDetailsAdminRead(
        bank_name=stored.bank_name,
        account_holder_name=stored.account_holder_name,
        sort_code=domain.format_sort_code(
            decrypt_text(stored.sort_code_ciphertext, key=get_settings().payout_details_key)
        ),
        account_number=decrypt_text(stored.account_number_ciphertext, key=get_settings().payout_details_key),
        updated_at=stored.updated_at,
    )


async def list_redeemed_referrals(
    session: AsyncSession,
    *,
    limit: int,
    cursor: dict[str, Any] | None = None,
    payout_status: str | None = None,
) -> tuple[list[ReferralAdminRead], str | None]:
    """The settlement queue, newest referral first.

    Emails and bank details are each resolved in one lookup rather than per
    row, to avoid a join per row on a screen read far more often than it is
    written.
    """
    status = domain.normalise_payout_status(payout_status) if payout_status else None
    referrals, next_cursor = await repository.redeemed_referrals_page(
        session, limit=limit, cursor=cursor, payout_status=status
    )
    ids = {referral.referrer_user_id for referral in referrals} | {
        referral.referred_user_id for referral in referrals if referral.referred_user_id is not None
    }
    people = await identity.user_refs_by_ids(session, list(ids))
    payout_details = await repository.payout_details_by_user_ids(
        session, [referral.referrer_user_id for referral in referrals]
    )
    admin_reads: list[ReferralAdminRead] = []
    for referral in referrals:
        referrer = people.get(referral.referrer_user_id)
        referred = people.get(referral.referred_user_id) if referral.referred_user_id else None
        admin_reads.append(
            ReferralAdminRead(
                id=referral.id,
                code=referral.code,
                referrer_email=referrer.email if referrer else str(referral.referrer_user_id),
                referred_email=referred.email if referred else None,
                redeemed_at=referral.redeemed_at,
                earned_pence=referral.earned_pence,
                payout_status=referral.payout_status,
                paid_at=referral.paid_at,
                payout_reference=referral.payout_reference,
                payout_details=_admin_payout_details(payout_details.get(referral.referrer_user_id)),
            )
        )
    return admin_reads, next_cursor


async def set_referral_payout(
    session: AsyncSession,
    referral_id: uuid.UUID,
    *,
    payout_status: str,
    payout_reference: str | None,
    actor_user_id: uuid.UUID,
    now: datetime,
) -> ReferralAdminRead:
    """Record that a referral has been settled, or that it has not after all.

    Reversible: marking it unpaid clears the stamp rather than leaving a paid
    date on an unpaid row.
    """
    status = domain.normalise_payout_status(payout_status)
    referral = await repository.referral_by_id(session, referral_id)
    if referral is None:
        raise errors.ReferralNotFound()
    if referral.redeemed_at is None:
        raise errors.ReferralNotRedeemed()
    paid = status == "paid"
    await repository.set_payout(
        session,
        referral_id,
        payout_status=status,
        payout_reference=payout_reference if paid else None,
        paid_at=now if paid else None,
        paid_by_user_id=actor_user_id if paid else None,
    )
    refreshed = await repository.referral_by_id(session, referral_id)
    if refreshed is None:  # pragma: no cover - the row was just written
        raise errors.ReferralNotFound()
    return await _referral_admin_read(session, refreshed)


async def _referral_admin_read(session: AsyncSession, referral) -> ReferralAdminRead:  # type: ignore[no-untyped-def]
    """Shape one referral for the settlement queue, resolving both people's emails and bank details."""
    ids = [referral.referrer_user_id] + ([referral.referred_user_id] if referral.referred_user_id else [])
    people = await identity.user_refs_by_ids(session, ids)
    referrer = people.get(referral.referrer_user_id)
    referred = people.get(referral.referred_user_id) if referral.referred_user_id else None
    payout_details = await repository.payout_details_by_user(session, referral.referrer_user_id)
    return ReferralAdminRead(
        id=referral.id,
        code=referral.code,
        referrer_email=referrer.email if referrer else str(referral.referrer_user_id),
        referred_email=referred.email if referred else None,
        redeemed_at=referral.redeemed_at,
        earned_pence=referral.earned_pence,
        payout_status=referral.payout_status,
        paid_at=referral.paid_at,
        payout_reference=referral.payout_reference,
        payout_details=_admin_payout_details(payout_details),
    )
