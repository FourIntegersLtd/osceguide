"""Storage for partner attribution and referrals."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import keyset_page
from app.features.growth.models import Acquisition, PartnerArrival, PartnerReporter, Referral


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
    stmt = (
        select(PartnerArrival)
        .where(PartnerArrival.visitor_key == visitor_key)
        .order_by(PartnerArrival.landed_at.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def acquisition_for(session: AsyncSession, user_id: uuid.UUID) -> Acquisition | None:
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
    stmt = select(Acquisition.user_id).where(Acquisition.partner == partner)
    return list((await session.execute(stmt)).scalars())


async def is_reporter(session: AsyncSession, *, partner: str, email: str) -> bool:
    stmt = select(PartnerReporter.id).where(
        PartnerReporter.partner == partner,
        PartnerReporter.email == email,
        PartnerReporter.revoked_at.is_(None),
    )
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def add_reporter(session: AsyncSession, *, partner: str, email: str) -> PartnerReporter:
    reporter = PartnerReporter(partner=partner, email=email)
    session.add(reporter)
    await session.flush()
    await session.refresh(reporter)
    return reporter


# --- referrals -------------------------------------------------------------


async def referral_by_code(session: AsyncSession, code: str) -> Referral | None:
    stmt = select(Referral).where(Referral.code == code.strip().upper())
    return (await session.execute(stmt)).scalar_one_or_none()


async def create_referral(session: AsyncSession, *, referrer_user_id: uuid.UUID, code: str) -> Referral:
    referral = Referral(referrer_user_id=referrer_user_id, code=code.strip().upper())
    session.add(referral)
    await session.flush()
    await session.refresh(referral)
    return referral


async def referrals_for(session: AsyncSession, user_id: uuid.UUID) -> list[Referral]:
    stmt = select(Referral).where(Referral.referrer_user_id == user_id)
    return list((await session.execute(stmt)).scalars())


async def redeem(
    session: AsyncSession,
    referral_id: uuid.UUID,
    *,
    referred_user_id: uuid.UUID,
    earned_pence: int,
    at: datetime,
) -> None:
    await session.execute(
        update(Referral)
        .where(Referral.id == referral_id, Referral.redeemed_at.is_(None))
        .values(referred_user_id=referred_user_id, redeemed_at=at, earned_pence=earned_pence)
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


async def referral_by_id(session: AsyncSession, referral_id: uuid.UUID) -> Referral | None:
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
