"""Turns stored slots and sessions into what the marketplace routes return."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audience import AudienceOut
from app.features.identity import service as identity
from app.features.marketplace.models import AvailabilityPost, PeerSession
from app.features.marketplace.schemas import PeerSessionRead, PostRead


def peer_username(user: identity.UserRef | None) -> str:
    """The name the other person sees.

    The first word of their name in lower case, else the part of their email
    before the @, else "colleague".
    """
    if user is None:
        return "colleague"
    full_name = (user.name or "").strip()
    if full_name:
        return full_name.split()[0].lower()
    email_name = user.email.split("@", 1)[0]
    return email_name or "colleague"


def post_read(
    post: AvailabilityPost,
    exam_code: str,
    *,
    viewer_id: uuid.UUID,
    owner_username: str,
    claimed_by_username: str | None = None,
) -> PostRead:
    return PostRead(
        id=post.id,
        owner_user_id=post.owner_user_id,
        owner_username=owner_username,
        claimed_by_user_id=post.claimed_by_user_id,
        claimed_by_username=claimed_by_username,
        exam_code=exam_code,
        starts_at=post.starts_at,
        duration_minutes=post.duration_minutes,
        note=post.note,
        status=post.status,
        is_mine=post.owner_user_id == viewer_id,
        audience=AudienceOut.of(post),
    )


def session_read(
    peer_session: PeerSession,
    exam_code: str,
    *,
    viewer_id: uuid.UUID,
    partner_username: str,
) -> PeerSessionRead:
    """One booked session, as the viewer sees it.

    Two different roles come back. `user_role` says whether the viewer offered
    the slot ("poster") or claimed it ("claimer"). `my_role` says whether they play
    the doctor or the patient, and is only known once someone has joined.
    """
    viewer_is_owner = peer_session.owner_user_id == viewer_id
    partner_user_id = peer_session.claimer_user_id if viewer_is_owner else peer_session.owner_user_id
    user_role = "poster" if viewer_is_owner else "claimer"
    my_role: str | None = None
    if peer_session.doctor_user_id and peer_session.patient_user_id:
        if viewer_id == peer_session.doctor_user_id:
            my_role = "doctor"
        elif viewer_id == peer_session.patient_user_id:
            my_role = "patient"
    return PeerSessionRead(
        id=peer_session.id,
        exam_code=exam_code,
        starts_at=peer_session.starts_at,
        status=peer_session.status,
        room_name=peer_session.room_name,
        partner_user_id=partner_user_id,
        partner_username=partner_username,
        user_role=user_role,
        practice_session_id=peer_session.practice_session_id,
        my_role=my_role,
    )


async def posts_read(
    session: AsyncSession,
    posts: list[AvailabilityPost],
    exam_codes: dict[uuid.UUID, str],
    *,
    viewer_id: uuid.UUID,
) -> list[PostRead]:
    """Many slots at once, looking up every owner's and claimer's name in one query."""
    user_ids: set[uuid.UUID] = set()
    for post in posts:
        user_ids.add(post.owner_user_id)
        if post.claimed_by_user_id is not None:
            user_ids.add(post.claimed_by_user_id)
    users_by_id = await identity.user_refs_by_ids(session, list(user_ids))
    return [
        post_read(
            post,
            exam_codes.get(post.exam_id, ""),
            viewer_id=viewer_id,
            owner_username=peer_username(users_by_id.get(post.owner_user_id)),
            claimed_by_username=(
                peer_username(users_by_id.get(post.claimed_by_user_id))
                if post.claimed_by_user_id is not None
                else None
            ),
        )
        for post in posts
    ]
