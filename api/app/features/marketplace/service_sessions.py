"""Peer session lifecycle: listing, joining, cancelling."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog import service as catalog
from app.features.identity import service as identity
from app.features.marketplace import domain, errors, repository, service_reads
from app.features.marketplace.schemas import PeerSessionRead
from app.features.marketplace.service import _exam_codes


async def list_my_sessions(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    limit: int,
    cursor: dict[str, Any] | None = None,
) -> tuple[list[PeerSessionRead], str | None]:
    rows, next_cursor = await repository.sessions_for_user(session, user_id, limit=limit, cursor=cursor)
    exams = await _exam_codes(session, {r.exam_id for r in rows})
    partner_ids = {row.claimer_user_id if row.owner_user_id == user_id else row.owner_user_id for row in rows}
    people = await identity.user_refs_by_ids(session, list(partner_ids))
    return [
        service_reads.session_read(
            row,
            exams.get(row.exam_id, ""),
            viewer_id=user_id,
            partner_username=service_reads.peer_username(
                people.get(row.claimer_user_id if row.owner_user_id == user_id else row.owner_user_id)
            ),
        )
        for row in rows
    ], next_cursor


async def join_session(
    session: AsyncSession, session_id: uuid.UUID, *, user_id: uuid.UUID, now: datetime
) -> PeerSessionRead:
    from app.features.peer_practice.service_lifecycle import create_runtime_for_peer_booking

    row = await repository.peer_session_by_id(session, session_id)
    if row is None:
        raise errors.SessionNotFound()

    state = domain.SessionState(
        owner_id=str(row.owner_user_id),
        claimer_id=str(row.claimer_user_id),
        starts_at=row.starts_at,
    )
    if not domain.may_join(state, user_id=str(user_id)):
        raise errors.SessionNotFound()
    if not domain.is_open(state, now=now):
        raise errors.SessionNotOpen()

    if row.practice_session_id is None:
        practice = await create_runtime_for_peer_booking(
            session,
            peer_session_id=row.id,
            exam_id=row.exam_id,
            owner_user_id=row.owner_user_id,
            claimer_user_id=row.claimer_user_id,
        )
        await repository.link_practice_session(
            session,
            row.id,
            practice_session_id=practice.id,
            doctor_user_id=practice.doctor_user_id,
            patient_user_id=practice.patient_user_id,
        )
        row = await repository.peer_session_by_id(session, session_id)
        assert row is not None

    code = await catalog.exam_code_by_id(session, row.exam_id)
    partner_id = row.claimer_user_id if row.owner_user_id == user_id else row.owner_user_id
    partner = await identity.user_ref_by_id(session, partner_id)
    return service_reads.session_read(
        row, code or "", viewer_id=user_id, partner_username=service_reads.peer_username(partner)
    )


async def cancel_peer_session(
    session: AsyncSession, session_id: uuid.UUID, *, user_id: uuid.UUID, now: datetime
) -> None:
    row = await repository.peer_session_by_id(session, session_id)
    if row is None:
        raise errors.SessionNotFound()
    if user_id not in {row.owner_user_id, row.claimer_user_id}:
        raise errors.SessionNotFound()
    if not await repository.mark_peer_cancelled(session, session_id, at=now):
        raise errors.SessionNotOpen()
