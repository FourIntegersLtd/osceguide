"""Storage for availability posts and the sessions they create."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import encode_cursor
from app.features.marketplace.models import AvailabilityPost, PeerSession


async def create_post(
    session: AsyncSession,
    *,
    owner_user_id: uuid.UUID,
    exam_id: uuid.UUID,
    starts_at: datetime,
    duration_minutes: int,
    note: str | None,
) -> AvailabilityPost:
    row = AvailabilityPost(
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


async def list_by_owner(
    session: AsyncSession, owner_user_id: uuid.UUID, *, limit: int = 100
) -> list[AvailabilityPost]:
    """Every post this person offered, including claimed and cancelled history."""
    stmt = (
        select(AvailabilityPost)
        .where(AvailabilityPost.owner_user_id == owner_user_id)
        .order_by(AvailabilityPost.starts_at.desc())
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars())


async def list_open(
    session: AsyncSession,
    *,
    now: datetime,
    limit: int,
    cursor: dict[str, Any] | None = None,
    exam_id: uuid.UUID | None = None,
) -> tuple[list[AvailabilityPost], str | None]:
    """Slots still to come and still unclaimed."""
    stmt = select(AvailabilityPost).where(
        AvailabilityPost.status == "available", AvailabilityPost.starts_at > now
    )
    if exam_id is not None:
        stmt = stmt.where(AvailabilityPost.exam_id == exam_id)
    if cursor:
        stmt = stmt.where(AvailabilityPost.starts_at > datetime.fromisoformat(cursor["t"]))
    rows = list(
        (
            await session.execute(
                stmt.order_by(AvailabilityPost.starts_at, AvailabilityPost.id).limit(limit + 1)
            )
        ).scalars()
    )
    if len(rows) <= limit:
        return rows, None
    page = rows[:limit]
    return page, encode_cursor({"t": page[-1].starts_at, "i": str(page[-1].id)})


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
