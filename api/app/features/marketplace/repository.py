"""Storage for availability posts and the sessions they create."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audience import Audience, ViewerAudiences, addressed_to, visible_to
from app.core.pagination import keyset_page
from app.features.marketplace.models import AvailabilityPost, PeerSession


async def create_post(
    session: AsyncSession,
    *,
    audience: Audience,
    owner_user_id: uuid.UUID,
    exam_id: uuid.UUID,
    starts_at: datetime,
    duration_minutes: int,
    note: str | None,
) -> AvailabilityPost:
    row = AvailabilityPost(
        visibility=str(audience.visibility),
        audience_org_id=audience.org_id,
        audience_group_id=audience.group_id,
        owner_user_id=owner_user_id,
        exam_id=exam_id,
        starts_at=starts_at,
        duration_minutes=duration_minutes,
        note=note,
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def post_by_id(session: AsyncSession, post_id: uuid.UUID) -> AvailabilityPost | None:
    stmt = select(AvailabilityPost).where(AvailabilityPost.id == post_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def lock_post(session: AsyncSession, post_id: uuid.UUID) -> AvailabilityPost | None:
    """Read a post for update, holding the row until the transaction ends.

    This is the whole safety of a claim: two people press the button at the same
    moment, and the second waits here, then reads the status the first wrote.
    Checking without the lock means both see `available` and both win.
    """
    stmt = select(AvailabilityPost).where(AvailabilityPost.id == post_id).with_for_update()
    return (await session.execute(stmt)).scalar_one_or_none()


async def mark_claimed(
    session: AsyncSession, post_id: uuid.UUID, *, claimer_user_id: uuid.UUID, at: datetime
) -> None:
    await session.execute(
        update(AvailabilityPost)
        .where(AvailabilityPost.id == post_id)
        .values(status="claimed", claimed_by_user_id=claimer_user_id, claimed_at=at)
    )


async def mark_cancelled(session: AsyncSession, post_id: uuid.UUID, *, at: datetime) -> None:
    await session.execute(
        update(AvailabilityPost)
        .where(AvailabilityPost.id == post_id)
        .values(status="cancelled", cancelled_at=at)
    )


async def list_open(
    session: AsyncSession,
    *,
    viewer: ViewerAudiences,
    now: datetime,
    limit: int,
    cursor: dict[str, Any] | None = None,
    exam_id: uuid.UUID | None = None,
    audience: Audience | None = None,
) -> tuple[list[AvailabilityPost], str | None]:
    """Slots still to come, still unclaimed, and offered to a room this viewer
    is in."""
    stmt = select(AvailabilityPost).where(
        AvailabilityPost.status == "available",
        AvailabilityPost.starts_at > now,
        visible_to(AvailabilityPost, viewer),
    )
    if exam_id is not None:
        stmt = stmt.where(AvailabilityPost.exam_id == exam_id)
    if audience is not None:
        stmt = stmt.where(addressed_to(AvailabilityPost, audience))
    return await keyset_page(
        session,
        stmt,
        sort_col=AvailabilityPost.starts_at,
        id_col=AvailabilityPost.id,
        limit=limit,
        cursor=cursor,
        descending=False,
    )


async def create_peer_session(
    session: AsyncSession,
    *,
    post_id: uuid.UUID,
    owner_user_id: uuid.UUID,
    claimer_user_id: uuid.UUID,
    exam_id: uuid.UUID,
    starts_at: datetime,
) -> PeerSession:
    row = PeerSession(
        post_id=post_id,
        owner_user_id=owner_user_id,
        claimer_user_id=claimer_user_id,
        exam_id=exam_id,
        starts_at=starts_at,
        room_name=None,
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def set_room(session: AsyncSession, session_id: uuid.UUID, *, room_name: str) -> None:
    await session.execute(update(PeerSession).where(PeerSession.id == session_id).values(room_name=room_name))


async def peer_session_by_id(session: AsyncSession, session_id: uuid.UUID) -> PeerSession | None:
    stmt = select(PeerSession).where(PeerSession.id == session_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def sessions_for_user(
    session: AsyncSession, user_id: uuid.UUID, *, limit: int = 50
) -> list[PeerSession]:
    stmt = (
        select(PeerSession)
        .where(
            or_(
                PeerSession.owner_user_id == user_id,
                PeerSession.claimer_user_id == user_id,
            )
        )
        .order_by(PeerSession.starts_at.desc())
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars())
