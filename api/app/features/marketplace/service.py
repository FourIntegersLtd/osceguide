"""Offering, claiming and joining peer practice slots."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audience import (
    PUBLIC,
    Audience,
    AudienceOut,
    audience_of,
    audiences_for,
    can_see,
    ensure_may_address,
)
from app.core.errors import AppError, raise_mapped
from app.features.attempts import service as attempts
from app.features.catalog import service as catalog
from app.features.catalog.service import resolve_exam
from app.features.marketplace import domain, errors, repository
from app.features.marketplace.models import AvailabilityPost, PeerSession
from app.features.marketplace.schemas import PeerSessionRead, PostRead

_REFUSALS: dict[type[Exception], type[AppError]] = {
    domain.PostUnavailable: errors.PostUnavailableError,
    domain.CannotClaimOwnPost: errors.CannotClaimOwnPostError,
    domain.NotYours: errors.NotYoursError,
}


def _state(post: AvailabilityPost) -> domain.PostState:
    return domain.PostState(status=post.status, owner_id=str(post.owner_user_id), starts_at=post.starts_at)


async def offer_slot(
    session: AsyncSession,
    *,
    owner_user_id: uuid.UUID,
    exam_code: str,
    starts_at: datetime,
    duration_minutes: int,
    note: str | None,
    now: datetime,
    audience: Audience = PUBLIC,
) -> PostRead:
    """Offer to practise with somebody, at a time.

    Gated on the same entitlement an attempt is, free trial included: a slot is
    an arrangement to sit a station with a real partner, which is the paid
    product rather than an advert for it. Offering one for an exam you do not
    hold would also put it in front of people who do.
    """
    exam = await resolve_exam(session, exam_code)
    await attempts.require_entitlement(session, user_id=owner_user_id, exam_id=exam.id, now=now)
    ensure_may_address(audience, await audiences_for(session, owner_user_id))
    row = await repository.create_post(
        session,
        audience=audience,
        owner_user_id=owner_user_id,
        exam_id=exam.id,
        starts_at=starts_at,
        duration_minutes=duration_minutes,
        note=note,
    )
    return _post_read(row, exam.code, viewer_id=owner_user_id)


async def claim_slot(
    session: AsyncSession, post_id: uuid.UUID, *, claimer_user_id: uuid.UUID, now: datetime
) -> PeerSessionRead:
    """Take a peer's offered slot, once.

    The row is locked before it is examined, so two people pressing the button
    at the same moment serialise here: the second waits, then reads the status
    the first wrote and is told the slot is gone. Checking without the lock
    means both see `available` and both believe they won.

    Entitlement is checked after the audience, and for the same reason it is
    checked at all: claiming puts somebody in a live room for that exam.
    """
    post = await repository.lock_post(session, post_id)
    if post is None:
        raise errors.PostNotFound()
    if not can_see(audience_of(post), await audiences_for(session, claimer_user_id)):
        # Not found rather than forbidden: a slot offered inside an institution
        # must not be discoverable by anyone holding its id.
        raise errors.PostNotFound()

    await attempts.require_entitlement(session, user_id=claimer_user_id, exam_id=post.exam_id, now=now)

    try:
        domain.ensure_claimable(_state(post), claimer_id=str(claimer_user_id), now=now)
    except Exception as exc:  # noqa: BLE001 - mapped above
        raise_mapped(exc, _REFUSALS)

    await repository.mark_claimed(session, post_id, claimer_user_id=claimer_user_id, at=now)
    peer_session = await repository.create_peer_session(
        session,
        post_id=post.id,
        owner_user_id=post.owner_user_id,
        claimer_user_id=claimer_user_id,
        exam_id=post.exam_id,
        starts_at=post.starts_at,
    )
    # Derived from the session id, so a stray room says what it belongs to.
    await repository.set_room(session, peer_session.id, room_name=f"peer_{peer_session.id}")
    refreshed = await repository.peer_session_by_id(session, peer_session.id)
    code = await catalog.exam_code_by_id(session, post.exam_id)
    return _session_read(refreshed, code or "", viewer_id=claimer_user_id)  # type: ignore[arg-type]


async def withdraw_slot(
    session: AsyncSession, post_id: uuid.UUID, *, actor_id: uuid.UUID, now: datetime
) -> None:
    post = await repository.lock_post(session, post_id)
    if post is None:
        raise errors.PostNotFound()
    try:
        domain.ensure_cancellable(_state(post), actor_id=str(actor_id))
    except Exception as exc:  # noqa: BLE001 - mapped above
        raise_mapped(exc, _REFUSALS)
    await repository.mark_cancelled(session, post_id, at=now)


async def list_open_slots(
    session: AsyncSession,
    *,
    viewer_id: uuid.UUID,
    now: datetime,
    limit: int,
    cursor: dict[str, Any] | None,
    audience: Audience | None = None,
) -> tuple[list[PostRead], str | None]:
    viewer = await audiences_for(session, viewer_id)
    rows, next_cursor = await repository.list_open(
        session, viewer=viewer, now=now, limit=limit, cursor=cursor, audience=audience
    )
    exams = await _exam_codes(session, {r.exam_id for r in rows})
    return [_post_read(row, exams.get(row.exam_id, ""), viewer_id=viewer_id) for row in rows], next_cursor


async def _exam_codes(session: AsyncSession, exam_ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    """One lookup per distinct exam, not one per row."""
    codes: dict[uuid.UUID, str] = {}
    for exam_id in exam_ids:
        code = await catalog.exam_code_by_id(session, exam_id)
        if code is not None:
            codes[exam_id] = code
    return codes


async def list_my_posts(
    session: AsyncSession, *, viewer_id: uuid.UUID, limit: int = 100
) -> list[PostRead]:
    """Every post this person offered, including claimed and cancelled history."""
    rows = await repository.list_by_owner(session, viewer_id, limit=limit)
    exams = await _exam_codes(session, {r.exam_id for r in rows})
    return [_post_read(row, exams.get(row.exam_id, ""), viewer_id=viewer_id) for row in rows]


async def list_my_sessions(session: AsyncSession, user_id: uuid.UUID) -> list[PeerSessionRead]:
    rows = await repository.sessions_for_user(session, user_id)
    exams = await _exam_codes(session, {r.exam_id for r in rows})
    return [_session_read(row, exams.get(row.exam_id, ""), viewer_id=user_id) for row in rows]


async def join_session(
    session: AsyncSession, session_id: uuid.UUID, *, user_id: uuid.UUID, now: datetime
) -> PeerSessionRead:
    row = await repository.peer_session_by_id(session, session_id)
    if row is None:
        raise errors.SessionNotFound()

    state = domain.SessionState(
        owner_id=str(row.owner_user_id),
        claimer_id=str(row.claimer_user_id),
        starts_at=row.starts_at,
    )
    if not domain.may_join(state, user_id=str(user_id)):
        # 404 rather than 403: a session id is not something a stranger should
        # be able to confirm exists.
        raise errors.SessionNotFound()
    if not domain.is_open(state, now=now):
        raise errors.SessionNotOpen()

    code = await catalog.exam_code_by_id(session, row.exam_id)
    return _session_read(row, code or "", viewer_id=user_id)


def _post_read(row: AvailabilityPost, exam_code: str, *, viewer_id: uuid.UUID) -> PostRead:
    return PostRead(
        id=row.id,
        owner_user_id=row.owner_user_id,
        exam_code=exam_code,
        starts_at=row.starts_at,
        duration_minutes=row.duration_minutes,
        note=row.note,
        status=row.status,
        is_mine=row.owner_user_id == viewer_id,
        audience=AudienceOut.of(row),
    )


def _session_read(row: PeerSession, exam_code: str, *, viewer_id: uuid.UUID) -> PeerSessionRead:
    partner = row.claimer_user_id if row.owner_user_id == viewer_id else row.owner_user_id
    return PeerSessionRead(
        id=row.id,
        exam_code=exam_code,
        starts_at=row.starts_at,
        status=row.status,
        room_name=row.room_name,
        partner_user_id=partner,
    )
