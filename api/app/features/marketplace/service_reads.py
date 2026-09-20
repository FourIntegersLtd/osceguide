"""Shapes the marketplace routes return."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audience import AudienceOut
from app.features.identity import service as identity
from app.features.marketplace.models import AvailabilityPost, PeerSession
from app.features.marketplace.schemas import PeerSessionRead, PostRead


def peer_username(ref: identity.UserRef | None) -> str:
    if ref is None:
        return "colleague"
    name = (ref.name or "").strip()
    if name:
        return name.split()[0].lower()
    local = ref.email.split("@", 1)[0]
    return local or "colleague"


def post_read(
    row: AvailabilityPost,
    exam_code: str,
    *,
    viewer_id: uuid.UUID,
    owner_username: str,
    claimed_by_username: str | None = None,
) -> PostRead:
    return PostRead(
        id=row.id,
        owner_user_id=row.owner_user_id,
        owner_username=owner_username,
        claimed_by_user_id=row.claimed_by_user_id,
        claimed_by_username=claimed_by_username,
        exam_code=exam_code,
        starts_at=row.starts_at,
        duration_minutes=row.duration_minutes,
        note=row.note,
        status=row.status,
        is_mine=row.owner_user_id == viewer_id,
        audience=AudienceOut.of(row),
    )


def session_read(
    row: PeerSession,
    exam_code: str,
    *,
    viewer_id: uuid.UUID,
    partner_username: str,
) -> PeerSessionRead:
    partner = row.claimer_user_id if row.owner_user_id == viewer_id else row.owner_user_id
    role = "poster" if row.owner_user_id == viewer_id else "claimer"
    my_role: str | None = None
    if row.doctor_user_id and row.patient_user_id:
        if viewer_id == row.doctor_user_id:
            my_role = "doctor"
        elif viewer_id == row.patient_user_id:
            my_role = "patient"
    return PeerSessionRead(
        id=row.id,
        exam_code=exam_code,
        starts_at=row.starts_at,
        status=row.status,
        room_name=row.room_name,
        partner_user_id=partner,
        partner_username=partner_username,
        user_role=role,
        practice_session_id=row.practice_session_id,
        my_role=my_role,
    )


async def posts_read(
    session: AsyncSession,
    rows: list[AvailabilityPost],
    exams: dict[uuid.UUID, str],
    *,
    viewer_id: uuid.UUID,
) -> list[PostRead]:
    user_ids: set[uuid.UUID] = set()
    for row in rows:
        user_ids.add(row.owner_user_id)
        if row.claimed_by_user_id is not None:
            user_ids.add(row.claimed_by_user_id)
    people = await identity.user_refs_by_ids(session, list(user_ids))
    return [
        post_read(
            row,
            exams.get(row.exam_id, ""),
            viewer_id=viewer_id,
            owner_username=peer_username(people.get(row.owner_user_id)),
            claimed_by_username=(
                peer_username(people.get(row.claimed_by_user_id))
                if row.claimed_by_user_id is not None
                else None
            ),
        )
        for row in rows
    ]
