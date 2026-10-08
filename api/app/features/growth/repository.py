"""Storage for partner attribution and referrals."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import Select, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import keyset_page
from app.core.search import contains_text
from app.features.growth.models import (
    Acquisition,
    PartnerArrival,
    PartnerPilotConfig,
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
    """Grant this email reporting access to this one partner's numbers.

    One row per (partner, email): adding someone already there is a no-op, and adding
    someone whose access was revoked makes the same row live again.
    """
    existing = (
        await session.execute(
            select(PartnerReporter).where(PartnerReporter.partner == partner, PartnerReporter.email == email)
        )
    ).scalar_one_or_none()
    if existing is not None:
        existing.revoked_at = None
        await session.flush()
        return existing
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


async def redemption_made_at(
    session: AsyncSession, referred_user_id: uuid.UUID, redeemed_at: datetime
) -> Referral | None:
    """The credit one purchase earned, that still carries earnings.

    A redeemed row has no payment id, but it is stamped with the same instant as the payment it
    came from (one webhook transaction, one `now`), so buyer and instant name the purchase.
    """
    stmt = select(Referral).where(
        Referral.referred_user_id == referred_user_id,
        Referral.redeemed_at == redeemed_at,
        Referral.earned_pence > 0,
    )
    # No payment id is stored on a redeemed row, so a unique key would need a migration (left, noted).
    # Two redemptions at one instant are possible in principle; take the first, deterministically.
    return (await session.execute(stmt.order_by(Referral.id).limit(1))).scalar_one_or_none()


async def voided_redemption_made_at(
    session: AsyncSession, referred_user_id: uuid.UUID, redeemed_at: datetime
) -> Referral | None:
    """The credit one purchase earned that a refund or dispute has since zeroed (see `redemption_made_at`)."""
    stmt = select(Referral).where(
        Referral.referred_user_id == referred_user_id,
        Referral.redeemed_at == redeemed_at,
        Referral.earned_pence == 0,
        Referral.clawback_of_id.is_(None),
    )
    return (await session.execute(stmt.order_by(Referral.id).limit(1))).scalar_one_or_none()


async def set_earned(session: AsyncSession, credit: Referral, earned_pence: int) -> None:
    """Change what a redeemed row earned its referrer, as when a won dispute gives it back."""
    credit.earned_pence = earned_pence
    await session.flush()


async def clawback_of(session: AsyncSession, credit_id: uuid.UUID) -> Referral | None:
    """The negative row that already takes this paid-out credit back, if one was recorded."""
    stmt = select(Referral).where(Referral.clawback_of_id == credit_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def void_credit(session: AsyncSession, credit: Referral) -> None:
    """Zero a redeemed row's earnings. The row stays, so the sale is still on record."""
    credit.earned_pence = 0
    await session.flush()


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
    clawback_of_id: uuid.UUID | None = None,
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
        clawback_of_id=clawback_of_id,
    )
    session.add(redemption)
    await session.flush()
    return redemption


async def my_redeemed_referrals_page(
    session: AsyncSession,
    *,
    referrer_user_id: uuid.UUID,
    limit: int,
    cursor: dict[str, Any] | None = None,
    matching_referee_ids: Sequence[uuid.UUID] | None = None,
) -> tuple[list[Referral], str | None]:
    """This person's own redeemed referrals, newest first, keyset-paginated.

    `matching_referee_ids` narrows to referrals whose `referred_user_id` is in
    the set — the caller resolves a `search` string to matching user ids first
    (`identity.service.user_ids_matching`), since the referral row itself
    carries no email and this repository does not own `identity.User`.
    """
    stmt = select(Referral).where(
        Referral.referrer_user_id == referrer_user_id, Referral.redeemed_at.is_not(None)
    )
    if matching_referee_ids is not None:
        stmt = stmt.where(Referral.referred_user_id.in_(matching_referee_ids))
    return await keyset_page(
        session,
        stmt,
        sort_col=Referral.redeemed_at,
        id_col=Referral.id,
        limit=limit,
        cursor=cursor,
        descending=True,
    )


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


async def owed_referral_totals(session: AsyncSession) -> tuple[int, int, int]:
    """Pence owed, referrals owed and distinct referrers owed, over every redeemed unpaid row."""
    stmt = select(
        func.coalesce(func.sum(Referral.earned_pence), 0),
        # The pence net a clawback row off; the count is of sales owed, and a clawback is not one.
        func.count().filter(Referral.clawback_of_id.is_(None)),
        func.count(func.distinct(Referral.referrer_user_id)),
    ).where(Referral.redeemed_at.is_not(None), Referral.payout_status == "unpaid")
    owed, referrals, referrers = (await session.execute(stmt)).one()
    return int(owed), int(referrals), int(referrers)


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


# --- reconciliation and spend (G-1) ------------------------------------------------


async def count_arrivals_between(
    session: AsyncSession,
    partner: str,
    *,
    landed_from: datetime,
    landed_before: datetime,
    exam_code: str | None = None,
    utm_campaign: str | None = None,
) -> int:
    """Raw arrivals from this partner's links in a window, every visit counted."""
    stmt = select(func.count(PartnerArrival.id)).where(
        PartnerArrival.partner == partner,
        PartnerArrival.landed_at >= landed_from,
        PartnerArrival.landed_at < landed_before,
    )
    if exam_code is not None:
        stmt = stmt.where(PartnerArrival.exam_code == exam_code)
    if utm_campaign is not None:
        stmt = stmt.where(PartnerArrival.utm["utm_campaign"].astext == utm_campaign)
    return int((await session.execute(stmt)).scalar_one())


async def first_arrival_at(session: AsyncSession, partner: str) -> datetime | None:
    """When this partner's first visitor landed, or None if nobody has."""
    stmt = select(func.min(PartnerArrival.landed_at)).where(PartnerArrival.partner == partner)
    return (await session.execute(stmt)).scalar_one()


def _narrow_arrivals(stmt: Select[Any], *, exam_code: str | None, utm_campaign: str | None) -> Select[Any]:
    """Apply b2c's `exam` and `utm_campaign` filters to an arrival query."""
    if exam_code is not None:
        stmt = stmt.where(PartnerArrival.exam_code == exam_code)
    if utm_campaign is not None:
        stmt = stmt.where(PartnerArrival.utm["utm_campaign"].astext == utm_campaign)
    return stmt


def _narrow_acquisitions(
    stmt: Select[Any], *, exam_code: str | None, utm_campaign: str | None
) -> Select[Any]:
    """Apply b2c's `original_exam` and `original_campaign` filters to an
    acquisition query. The campaign lives on the arrival that earned the
    acquisition, so it is matched through `arrival_id` (an acquisition whose
    arrival was deleted carries no campaign and never matches a campaign filter)."""
    if exam_code is not None:
        stmt = stmt.where(Acquisition.exam_code == exam_code)
    if utm_campaign is not None:
        stmt = stmt.where(
            Acquisition.arrival_id.in_(
                select(PartnerArrival.id).where(PartnerArrival.utm["utm_campaign"].astext == utm_campaign)
            )
        )
    return stmt


async def acquired_user_ids_between(
    session: AsyncSession,
    partner: str,
    *,
    acquired_from: datetime,
    acquired_before: datetime,
    exam_code: str | None = None,
    utm_campaign: str | None = None,
) -> list[uuid.UUID]:
    """The people this partner was credited with in a window, optionally narrowed
    to one exam and/or the campaign that brought them."""
    stmt = select(Acquisition.user_id).where(
        Acquisition.partner == partner,
        Acquisition.acquired_at >= acquired_from,
        Acquisition.acquired_at < acquired_before,
    )
    stmt = _narrow_acquisitions(stmt, exam_code=exam_code, utm_campaign=utm_campaign)
    return list((await session.execute(stmt)).scalars())


async def pilot_config(session: AsyncSession, partner: str) -> PartnerPilotConfig | None:
    """This partner's stored pilot settings, or None while the defaults apply."""
    stmt = select(PartnerPilotConfig).where(PartnerPilotConfig.partner == partner)
    return (await session.execute(stmt)).scalar_one_or_none()


async def unique_arrival_count(
    session: AsyncSession,
    partner: str,
    *,
    landed_from: datetime,
    landed_before: datetime,
    exam_code: str | None = None,
    utm_campaign: str | None = None,
) -> int:
    """How many distinct visitors landed from this partner's links in a window.

    `count_arrivals_between` counts every visit; a visitor who follows the
    same link twice inflates that raw count without inflating this one.
    """
    stmt = select(func.count(func.distinct(PartnerArrival.visitor_key))).where(
        PartnerArrival.partner == partner,
        PartnerArrival.landed_at >= landed_from,
        PartnerArrival.landed_at < landed_before,
    )
    if exam_code is not None:
        stmt = stmt.where(PartnerArrival.exam_code == exam_code)
    if utm_campaign is not None:
        stmt = stmt.where(PartnerArrival.utm["utm_campaign"].astext == utm_campaign)
    return int((await session.execute(stmt)).scalar_one())


async def arrivals_page(
    session: AsyncSession,
    partner: str,
    *,
    landed_from: datetime,
    landed_before: datetime,
    exam_code: str | None,
    utm_campaign: str | None,
    search: str | None,
    limit: int,
    cursor: dict[str, Any] | None,
) -> tuple[list[PartnerArrival], str | None]:
    """A partner's raw arrivals in a window, newest first, keyset-paginated.

    `search` matches a fragment of the visitor key or the reference id — the
    two identifiers a support conversation about one visit is likely to quote.
    """
    stmt = select(PartnerArrival).where(
        PartnerArrival.partner == partner,
        PartnerArrival.landed_at >= landed_from,
        PartnerArrival.landed_at < landed_before,
    )
    if exam_code is not None:
        stmt = stmt.where(PartnerArrival.exam_code == exam_code)
    if utm_campaign is not None:
        stmt = stmt.where(PartnerArrival.utm["utm_campaign"].astext == utm_campaign)
    if search:
        stmt = stmt.where(
            contains_text(PartnerArrival.visitor_key, search) | contains_text(PartnerArrival.ref_id, search)
        )
    return await keyset_page(
        session,
        stmt,
        sort_col=PartnerArrival.landed_at,
        id_col=PartnerArrival.id,
        limit=limit,
        cursor=cursor,
        descending=True,
    )


async def acquired_users_page(
    session: AsyncSession,
    partner: str,
    *,
    acquired_from: datetime,
    acquired_before: datetime,
    exam_code: str | None,
    utm_campaign: str | None,
    limit: int,
    cursor: dict[str, Any] | None,
) -> tuple[list[Acquisition], str | None]:
    """A partner's acquired users in a window, newest first, keyset-paginated."""
    stmt = select(Acquisition).where(
        Acquisition.partner == partner,
        Acquisition.acquired_at >= acquired_from,
        Acquisition.acquired_at < acquired_before,
    )
    stmt = _narrow_acquisitions(stmt, exam_code=exam_code, utm_campaign=utm_campaign)
    return await keyset_page(
        session,
        stmt,
        sort_col=Acquisition.acquired_at,
        id_col=Acquisition.id,
        limit=limit,
        cursor=cursor,
        descending=True,
    )


async def arrivals_by_ids(
    session: AsyncSession, arrival_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, PartnerArrival]:
    """Several arrivals in one query, keyed by id — for enriching a page of acquired
    users without one query per row."""
    if not arrival_ids:
        return {}
    stmt = select(PartnerArrival).where(PartnerArrival.id.in_(list(arrival_ids)))
    rows = (await session.execute(stmt)).scalars()
    return {row.id: row for row in rows}


async def reporters_for_partner(session: AsyncSession, partner: str) -> list[PartnerReporter]:
    """Every reporter ever granted access to this partner, active or revoked, newest first."""
    stmt = (
        select(PartnerReporter)
        .where(PartnerReporter.partner == partner)
        .order_by(PartnerReporter.created_at.desc())
    )
    return list((await session.execute(stmt)).scalars())


async def revoke_reporter(session: AsyncSession, *, partner: str, email: str) -> bool:
    """Take away this email's reporting access to one partner.

    Returns True if a live grant existed to revoke; False if it was already
    revoked or never existed, so the caller can answer `not_found` honestly.
    """
    result = await session.execute(
        update(PartnerReporter)
        .where(
            PartnerReporter.partner == partner,
            PartnerReporter.email == email,
            PartnerReporter.revoked_at.is_(None),
        )
        .values(revoked_at=func.now())
    )
    return bool(getattr(result, "rowcount", 0))


async def arrivals_over_time(
    session: AsyncSession,
    partner: str,
    *,
    landed_from: datetime,
    landed_before: datetime,
    exam_code: str | None,
    utm_campaign: str | None,
    bucket: str,
) -> list[tuple[datetime, int]]:
    """Raw arrival counts per `date_trunc(bucket, landed_at)` bucket.

    Only the buckets with at least one arrival; the caller (`service_dashboard`)
    gap-fills the empty ones so a chart's x-axis is continuous. `bucket` is
    `day`, `week` or `month`, passed straight to Postgres, so the caller must
    have already validated it.
    """
    period = func.date_trunc(bucket, PartnerArrival.landed_at).label("period")
    stmt = (
        select(period, func.count(PartnerArrival.id))
        .where(
            PartnerArrival.partner == partner,
            PartnerArrival.landed_at >= landed_from,
            PartnerArrival.landed_at < landed_before,
        )
        .group_by(period)
        .order_by(period)
    )
    if exam_code is not None:
        stmt = stmt.where(PartnerArrival.exam_code == exam_code)
    if utm_campaign is not None:
        stmt = stmt.where(PartnerArrival.utm["utm_campaign"].astext == utm_campaign)
    rows = (await session.execute(stmt)).all()
    return [(period_start, int(count)) for period_start, count in rows]


async def acquisitions_over_time(
    session: AsyncSession,
    partner: str,
    *,
    acquired_from: datetime,
    acquired_before: datetime,
    exam_code: str | None,
    utm_campaign: str | None,
    bucket: str,
) -> list[tuple[datetime, int]]:
    """Signup counts per `date_trunc(bucket, acquired_at)` bucket. Only the buckets
    with at least one acquisition; the caller gap-fills the rest."""
    period = func.date_trunc(bucket, Acquisition.acquired_at).label("period")
    stmt = (
        select(period, func.count(Acquisition.id))
        .where(
            Acquisition.partner == partner,
            Acquisition.acquired_at >= acquired_from,
            Acquisition.acquired_at < acquired_before,
        )
        .group_by(period)
        .order_by(period)
    )
    stmt = _narrow_acquisitions(stmt, exam_code=exam_code, utm_campaign=utm_campaign)
    rows = (await session.execute(stmt)).all()
    return [(period_start, int(count)) for period_start, count in rows]


async def visits_by_exam(
    session: AsyncSession,
    partner: str,
    *,
    landed_from: datetime,
    landed_before: datetime,
    exam_code: str | None = None,
    utm_campaign: str | None = None,
) -> dict[str, int]:
    """Raw arrival counts per exam in a window, keyed by exam code ("unknown"
    for an arrival whose reference named no pilot exam)."""
    stmt = (
        select(PartnerArrival.exam_code, func.count(PartnerArrival.id))
        .where(
            PartnerArrival.partner == partner,
            PartnerArrival.landed_at >= landed_from,
            PartnerArrival.landed_at < landed_before,
        )
        .group_by(PartnerArrival.exam_code)
    )
    stmt = _narrow_arrivals(stmt, exam_code=exam_code, utm_campaign=utm_campaign)
    rows = (await session.execute(stmt)).all()
    return {(exam_code or "unknown"): int(count) for exam_code, count in rows}


async def visits_by_campaign(
    session: AsyncSession,
    partner: str,
    *,
    landed_from: datetime,
    landed_before: datetime,
    exam_code: str | None = None,
    utm_campaign: str | None = None,
) -> dict[str, int]:
    """Raw arrival counts per UTM campaign in a window, keyed by campaign
    ("unknown" for an arrival with no campaign tag). Every campaign is returned;
    the caller keeps the top ten after merging in the signup side."""
    campaign = PartnerArrival.utm["utm_campaign"].astext.label("campaign")
    stmt = (
        select(campaign, func.count(PartnerArrival.id))
        .where(
            PartnerArrival.partner == partner,
            PartnerArrival.landed_at >= landed_from,
            PartnerArrival.landed_at < landed_before,
        )
        .group_by(campaign)
    )
    stmt = _narrow_arrivals(stmt, exam_code=exam_code, utm_campaign=utm_campaign)
    rows = (await session.execute(stmt)).all()
    return {(campaign_value or "unknown"): int(count) for campaign_value, count in rows}


async def acquisitions_with_campaign(
    session: AsyncSession,
    partner: str,
    *,
    acquired_from: datetime,
    acquired_before: datetime,
    exam_code: str | None = None,
    utm_campaign: str | None = None,
) -> list[tuple[uuid.UUID, str, str]]:
    """This partner's acquisitions in a window, each with the exam and UTM campaign
    of the arrival that earned it — for the partner-safe breakdown tables.

    A left join on `arrival_id`: an acquisition whose arrival has since been
    deleted (`SET NULL`) still counts, against "unknown" for both dimensions,
    rather than vanishing from the signup breakdown.
    """
    stmt = (
        select(
            Acquisition.user_id,
            Acquisition.exam_code,
            PartnerArrival.utm["utm_campaign"].astext,
        )
        .select_from(Acquisition)
        .outerjoin(PartnerArrival, PartnerArrival.id == Acquisition.arrival_id)
        .where(
            Acquisition.partner == partner,
            Acquisition.acquired_at >= acquired_from,
            Acquisition.acquired_at < acquired_before,
        )
    )
    stmt = _narrow_acquisitions(stmt, exam_code=exam_code, utm_campaign=utm_campaign)
    rows = (await session.execute(stmt)).all()
    return [(user_id, row_exam or "unknown", campaign or "unknown") for user_id, row_exam, campaign in rows]


async def save_pilot_config(session: AsyncSession, partner: str, **values: Any) -> PartnerPilotConfig:
    """Write this partner's pilot settings, creating the row on first save."""
    stmt = (
        insert(PartnerPilotConfig)
        .values(id=uuid.uuid4(), partner=partner, **values)
        .on_conflict_do_update(
            constraint="uq_partner_pilot_configs_partner", set_={**values, "updated_at": func.now()}
        )
        .returning(PartnerPilotConfig)
        .execution_options(populate_existing=True)
    )
    return (await session.execute(stmt)).scalar_one()
