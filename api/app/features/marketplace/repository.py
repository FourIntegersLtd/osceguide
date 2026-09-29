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
    """Offer a new slot, available to whoever the audience addresses."""
    post = AvailabilityPost(
        visibility=str(audience.visibility),
        audience_org_id=audience.org_id,
        audience_group_id=audience.group_id,
        owner_user_id=owner_user_id,
        exam_id=exam_id,
        starts_at=starts_at,
        duration_minutes=duration_minutes,
        note=note,
    )
    session.add(post)
    await session.flush()
    await session.refresh(post)
    return post


async def post_by_id(session: AsyncSession, post_id: uuid.UUID) -> AvailabilityPost | None:
    """One offered slot, or `None` if no such slot exists."""
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
    """Record who claimed a slot and when. Call this only while the post is locked."""
    await session.execute(
        update(AvailabilityPost)
        .where(AvailabilityPost.id == post_id)
        .values(status="claimed", claimed_by_user_id=claimer_user_id, claimed_at=at)
    )


async def mark_cancelled(session: AsyncSession, post_id: uuid.UUID, *, at: datetime) -> None:
    """Withdraw a slot: mark it cancelled as of `at`."""
    await session.execute(
        update(AvailabilityPost)
        .where(AvailabilityPost.id == post_id)
        .values(status="cancelled", cancelled_at=at)
    )


async def cancel_sessions_for_post(session: AsyncSession, post_id: uuid.UUID, *, at: datetime) -> None:
    """Cancel the session a slot booked, if it is still scheduled or under way."""
    await session.execute(
        update(PeerSession)
        .where(PeerSession.post_id == post_id, PeerSession.status.in_(("scheduled", "active")))
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


async def list_feed(
    session: AsyncSession,
    *,
    viewer: ViewerAudiences,
    limit: int,
    cursor: dict[str, Any] | None = None,
    exam_id: uuid.UUID | None = None,
    audience: Audience | None = None,
) -> tuple[list[AvailabilityPost], str | None]:
    """Open and claimed slots, latest start time first.

    Claimed slots stay in the feed because the app shows them under Scheduled and,
    once their time has passed, Completed.
    """
    stmt = select(AvailabilityPost).where(
        AvailabilityPost.status.in_(("available", "claimed")),
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
        descending=True,
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
    """Book the session created when a slot is claimed."""
    peer_session = PeerSession(
        post_id=post_id,
        owner_user_id=owner_user_id,
        claimer_user_id=claimer_user_id,
        exam_id=exam_id,
        starts_at=starts_at,
        room_name=None,
    )
    session.add(peer_session)
    await session.flush()
    await session.refresh(peer_session)
    return peer_session


async def set_room(session: AsyncSession, peer_session_id: uuid.UUID, *, room_name: str) -> None:
    """Record the LiveKit room the two people will join at the appointed time."""
    await session.execute(
        update(PeerSession).where(PeerSession.id == peer_session_id).values(room_name=room_name)
    )


async def link_practice_session(
    session: AsyncSession,
    peer_session_id: uuid.UUID,
    *,
    practice_session_id: uuid.UUID,
    doctor_user_id: uuid.UUID,
    patient_user_id: uuid.UUID,
) -> None:
    """Link the live practice session the first joiner created, and mark the session active."""
    await session.execute(
        update(PeerSession)
        .where(PeerSession.id == peer_session_id)
        .values(
            practice_session_id=practice_session_id,
            doctor_user_id=doctor_user_id,
            patient_user_id=patient_user_id,
            status="active",
        )
    )


async def mark_peer_cancelled(session: AsyncSession, peer_session_id: uuid.UUID, *, at: datetime) -> bool:
    """Cancel a session that is still scheduled or under way. False if it was neither."""
    cancelled_ids = await session.execute(
        update(PeerSession)
        .where(PeerSession.id == peer_session_id, PeerSession.status.in_(("scheduled", "active")))
        .values(status="cancelled", cancelled_at=at)
        .returning(PeerSession.id)
    )
    return cancelled_ids.scalar_one_or_none() is not None


async def peer_session_by_id(session: AsyncSession, peer_session_id: uuid.UUID) -> PeerSession | None:
    """One booked session, or `None` if no such session exists."""
    stmt = select(PeerSession).where(PeerSession.id == peer_session_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def sessions_for_post(session: AsyncSession, post_id: uuid.UUID) -> list[PeerSession]:
    """The session(s) a slot booked. A post can only be claimed once, so this is
    at most one row in practice, but `withdraw_slot` reads it as a list rather
    than assume that will always stay true."""
    stmt = select(PeerSession).where(PeerSession.post_id == post_id)
    return list((await session.execute(stmt)).scalars())


async def claim_due_reminders(
    session: AsyncSession, *, now: datetime, remind_before: datetime
) -> list[PeerSession]:
    """Take every scheduled session starting between `now` and `remind_before` that has
    not yet had its reminder queued, and mark it claimed in the same statement.

    A plain `SELECT` then `UPDATE` would let two workers polling at the same moment both
    read `reminder_sent_at IS NULL`, both decide the reminder is theirs to send, and both
    queue it. Folding the check into the `UPDATE`'s own `WHERE` and reading back only the
    rows it actually touched (`RETURNING`) is what makes the claim atomic: a second
    worker's identical statement, run a moment later, finds nothing left to claim.
    """
    claimed = await session.execute(
        update(PeerSession)
        .where(
            PeerSession.status == "scheduled",
            PeerSession.starts_at > now,
            PeerSession.starts_at <= remind_before,
            PeerSession.reminder_sent_at.is_(None),
        )
        .values(reminder_sent_at=now)
        .returning(PeerSession)
    )
    return list(claimed.scalars())


async def sessions_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    limit: int,
    cursor: dict[str, Any] | None = None,
) -> tuple[list[PeerSession], str | None]:
    """Every session this person offered or claimed, latest start time first."""
    stmt = select(PeerSession).where(
        or_(
            PeerSession.owner_user_id == user_id,
            PeerSession.claimer_user_id == user_id,
        )
    )
    return await keyset_page(
        session,
        stmt,
        sort_col=PeerSession.starts_at,
        id_col=PeerSession.id,
        limit=limit,
        cursor=cursor,
        descending=True,
    )
