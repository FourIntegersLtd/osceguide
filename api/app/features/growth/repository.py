"""Storage for partner attribution and referrals."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import keyset_page
from app.features.growth.models import (
    Acquisition,
    PartnerArrival,
    PartnerReporter,
    Referral,
    ReferralPayoutDetails,
)


async def record_arrival(
    session: AsyncSession,
    *,
    partner: str,
    exam_code: str | None,
    visitor_key: str,
    ref_id: str | None,
    landing_path: str | None,
    utm: dict[str, Any] | None,
) -> PartnerArrival:
    """Log one visit from a partner's link, before the visitor has an account."""
    arrival = PartnerArrival(
        partner=partner,
        exam_code=exam_code,
        visitor_key=visitor_key,
        ref_id=ref_id,
        landing_path=landing_path,
        utm=utm,
    )
    session.add(arrival)
    await session.flush()
    await session.refresh(arrival)
    return arrival


async def latest_arrival_for_visitor(session: AsyncSession, visitor_key: str) -> PartnerArrival | None:
    """The most recent arrival logged under this anonymous visitor key, if any."""
    stmt = (
        select(PartnerArrival)
        .where(PartnerArrival.visitor_key == visitor_key)
        .order_by(PartnerArrival.landed_at.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def acquisition_for(session: AsyncSession, user_id: uuid.UUID) -> Acquisition | None:
    """The partner this user was attributed to, if one was ever recorded."""
    stmt = select(Acquisition).where(Acquisition.user_id == user_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def record_acquisition(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    partner: str,
    exam_code: str | None,
    arrival_id: uuid.UUID | None,
    at: datetime,
) -> Acquisition | None:
    """Written once; a user already attributed is left alone."""
    if await acquisition_for(session, user_id) is not None:
        return None
    acquisition = Acquisition(
        user_id=user_id,
        partner=partner,
        exam_code=exam_code,
        arrival_id=arrival_id,
        acquired_at=at,
    )
    session.add(acquisition)
    await session.flush()
    await session.refresh(acquisition)
    return acquisition


async def counts_for_partner(
    session: AsyncSession, partner: str, *, since: datetime | None = None
) -> tuple[int, int]:
    """Arrivals and acquisitions. Purchases are counted by `billing`."""
    arrivals_stmt = select(func.count(PartnerArrival.id)).where(PartnerArrival.partner == partner)
    acquisitions_stmt = select(func.count(Acquisition.id)).where(Acquisition.partner == partner)
    if since is not None:
        arrivals_stmt = arrivals_stmt.where(PartnerArrival.landed_at >= since)
        acquisitions_stmt = acquisitions_stmt.where(Acquisition.acquired_at >= since)
    arrivals = int((await session.execute(arrivals_stmt)).scalar_one())
    acquisitions = int((await session.execute(acquisitions_stmt)).scalar_one())
    return arrivals, acquisitions


async def acquired_user_ids(session: AsyncSession, partner: str) -> list[uuid.UUID]:
    """Every user id this partner has ever been credited with acquiring."""
    stmt = select(Acquisition.user_id).where(Acquisition.partner == partner)
    return list((await session.execute(stmt)).scalars())


async def is_reporter(session: AsyncSession, *, partner: str, email: str) -> bool:
    """Whether this email may read this one partner's numbers."""
    stmt = select(PartnerReporter.id).where(
        PartnerReporter.partner == partner,
        PartnerReporter.email == email,
        PartnerReporter.revoked_at.is_(None),
    )
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def add_reporter(session: AsyncSession, *, partner: str, email: str) -> PartnerReporter:
    """Grant this email reporting access to this one partner's numbers."""
    reporter = PartnerReporter(partner=partner, email=email)
    session.add(reporter)
    await session.flush()
    await session.refresh(reporter)
    return reporter


# --- referrals -------------------------------------------------------------


async def shareable_code(session: AsyncSession, code: str) -> Referral | None:
    """The row for a code somebody shares, matched case-insensitively.

    Only an unredeemed row counts. Each purchase made with a code is its own
    redeemed row (see `record_redemption`), and one of those is a record of a
    sale, not a code anyone can use.
    """
    stmt = select(Referral).where(Referral.code == code.strip().upper(), Referral.redeemed_at.is_(None))
    return (await session.execute(stmt)).scalar_one_or_none()


async def create_referral(session: AsyncSession, *, referrer_user_id: uuid.UUID, code: str) -> Referral:
    """Store a fresh, unredeemed referral code for this person to share."""
    referral = Referral(referrer_user_id=referrer_user_id, code=code.strip().upper())
    session.add(referral)
    await session.flush()
    await session.refresh(referral)
    return referral


async def referrals_for(session: AsyncSession, user_id: uuid.UUID) -> list[Referral]:
    """Every referral this person has issued, redeemed or not."""
    stmt = select(Referral).where(Referral.referrer_user_id == user_id)
    return list((await session.execute(stmt)).scalars())


async def record_redemption(
    session: AsyncSession,
    *,
    referrer_user_id: uuid.UUID,
    redemption_code: str,
    referred_user_id: uuid.UUID,
    earned_pence: int,
    at: datetime,
    plan_code: str | None = None,
) -> Referral:
    """Store one purchase made with somebody's code, as a redeemed row the payout queue lists.

    The shared code itself stays unredeemed so it keeps working. `redemption_code` is that
    code with a suffix, because `referrals.code` is unique; the importer stores b2c's
    redemptions the same way. `plan_code` is what was bought, so the referrer's own history
    can show it without a join into `billing`.
    """
    redemption = Referral(
        referrer_user_id=referrer_user_id,
        code=redemption_code,
        referred_user_id=referred_user_id,
        redeemed_at=at,
        earned_pence=earned_pence,
        plan_code=plan_code,
    )
    session.add(redemption)
    await session.flush()
    return redemption


async def my_redeemed_referrals_page(
    session: AsyncSession, *, referrer_user_id: uuid.UUID, limit: int
) -> list[Referral]:
    """This person's own redeemed referrals, newest first, up to `limit` of them.

    Not keyset-paginated like the admin queue: the frontend does its own
    client-side paging and searching over a single, larger fetch (up to 500
    rows), so a plain offset-free `LIMIT` is all this needs.
    """
    stmt = (
        select(Referral)
        .where(Referral.referrer_user_id == referrer_user_id, Referral.redeemed_at.is_not(None))
        .order_by(Referral.redeemed_at.desc())
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars())


async def redeemed_referrals_page(
    session: AsyncSession,
    *,
    limit: int,
    cursor: dict[str, Any] | None = None,
    payout_status: str | None = None,
) -> tuple[list[Referral], str | None]:
    """The referrals somebody may owe money for, newest first.

    Only redeemed rows: an outstanding code is not a referral yet.
    """
    stmt = select(Referral).where(Referral.redeemed_at.is_not(None))
    if payout_status:
        stmt = stmt.where(Referral.payout_status == payout_status)
    return await keyset_page(
        session,
        stmt,
        sort_col=Referral.redeemed_at,
        id_col=Referral.id,
        limit=limit,
        cursor=cursor,
        descending=True,
    )


async def referral_by_id(session: AsyncSession, referral_id: uuid.UUID) -> Referral | None:
    """One referral by its id, or nothing if it does not exist."""
    stmt = select(Referral).where(Referral.id == referral_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def set_payout(
    session: AsyncSession,
    referral_id: uuid.UUID,
    *,
    payout_status: str,
    payout_reference: str | None,
    paid_at: datetime | None,
    paid_by_user_id: uuid.UUID | None,
) -> None:
    """Record whether a redeemed referral has been settled, and by whom."""
    await session.execute(
        update(Referral)
        .where(Referral.id == referral_id)
        .values(
            payout_status=payout_status,
            payout_reference=payout_reference,
            paid_at=paid_at,
            paid_by_user_id=paid_by_user_id,
        )
    )


# --- referral payout bank details --------------------------------------------


async def payout_details_by_user(session: AsyncSession, user_id: uuid.UUID) -> ReferralPayoutDetails | None:
    """This person's own stored bank details, if they have ever saved any."""
    stmt = select(ReferralPayoutDetails).where(ReferralPayoutDetails.user_id == user_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def payout_details_by_user_ids(
    session: AsyncSession, user_ids: list[uuid.UUID]
) -> dict[uuid.UUID, ReferralPayoutDetails]:
    """Several people's bank details in one query, keyed by user id.

    Used by the settlement queue, which shows one row per referral rather than
    per referrer — fetching per row would be the same query run once per row
    on the page.
    """
    if not user_ids:
        return {}
    stmt = select(ReferralPayoutDetails).where(ReferralPayoutDetails.user_id.in_(user_ids))
    rows = (await session.execute(stmt)).scalars()
    return {row.user_id: row for row in rows}


async def upsert_payout_details(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    bank_name: str,
    account_holder_name: str,
    sort_code_ciphertext: str,
    account_number_ciphertext: str,
) -> ReferralPayoutDetails:
    """Create this person's bank details, or overwrite the ones already on file.

    One row per person (`uq_referral_payout_details_user_id`): saving again is
    always a correction to the same destination, never a second one.
    """
    existing = await payout_details_by_user(session, user_id)
    if existing is None:
        details = ReferralPayoutDetails(
            user_id=user_id,
            bank_name=bank_name,
            account_holder_name=account_holder_name,
            sort_code_ciphertext=sort_code_ciphertext,
            account_number_ciphertext=account_number_ciphertext,
        )
        session.add(details)
        await session.flush()
        await session.refresh(details)
        return details
    existing.bank_name = bank_name
    existing.account_holder_name = account_holder_name
    existing.sort_code_ciphertext = sort_code_ciphertext
    existing.account_number_ciphertext = account_number_ciphertext
    await session.flush()
    # `updated_at` is set by Postgres (`onupdate=func.now()`), so the Python
    # object is left expired after the UPDATE; without this the caller's next
    # read of `updated_at` triggers a lazy load outside the request's async
    # context and raises `MissingGreenlet`.
    await session.refresh(existing)
    return existing
