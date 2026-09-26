"""What happens after a slot is claimed: listing your booked sessions, joining one, cancelling one."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog import service as catalog
from app.features.identity import service as identity
from app.features.marketplace import domain, errors, repository, service_reads
from app.features.marketplace.models import PeerSession
from app.features.marketplace.schemas import PeerSessionRead
from app.features.marketplace.service import _exam_codes


def _partner_id(peer_session: PeerSession, user_id: uuid.UUID) -> uuid.UUID:
    """The other person in this session, whichever role the viewer plays."""
    if peer_session.owner_user_id == user_id:
        return peer_session.claimer_user_id
    return peer_session.owner_user_id


async def list_my_sessions(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    limit: int,
    cursor: dict[str, Any] | None = None,
) -> tuple[list[PeerSessionRead], str | None]:
    """Every session this person has offered or claimed, latest start time first."""
    peer_sessions, next_cursor = await repository.sessions_for_user(
        session, user_id, limit=limit, cursor=cursor
    )
    exam_codes = await _exam_codes(session, {peer_session.exam_id for peer_session in peer_sessions})
    partner_ids = {_partner_id(peer_session, user_id) for peer_session in peer_sessions}
    users_by_id = await identity.user_refs_by_ids(session, list(partner_ids))
    return [
        service_reads.session_read(
            peer_session,
            exam_codes.get(peer_session.exam_id, ""),
            viewer_id=user_id,
            partner_username=service_reads.peer_username(users_by_id.get(_partner_id(peer_session, user_id))),
        )
        for peer_session in peer_sessions
    ], next_cursor


async def join_session(
    session: AsyncSession, peer_session_id: uuid.UUID, *, user_id: uuid.UUID, now: datetime
) -> PeerSessionRead:
    """Let one of the two people into their session, from twenty minutes before it
    starts until an hour after. A cancelled session cannot be joined.

    The first person to join creates the live practice session, which decides who
    plays the doctor and who plays the patient. The second joins that same one.
    Anyone else is told the session does not exist, so an id alone cannot confirm
    that it does.
    """
    from app.features.peer_practice.service_lifecycle import create_runtime_for_peer_booking

    peer_session = await repository.peer_session_by_id(session, peer_session_id)
    if peer_session is None:
        raise errors.SessionNotFound()

    state = domain.SessionState(
        owner_id=str(peer_session.owner_user_id),
        claimer_id=str(peer_session.claimer_user_id),
        starts_at=peer_session.starts_at,
        status=peer_session.status,
    )
    if not domain.may_join(state, user_id=str(user_id)):
        raise errors.SessionNotFound()
    try:
        domain.ensure_joinable(state, now=now)
    except domain.SessionNotJoinable as refusal:
        raise errors.SessionNotOpen(str(refusal)) from refusal

    if peer_session.practice_session_id is None:
        practice_session = await create_runtime_for_peer_booking(
            session,
            peer_session_id=peer_session.id,
            exam_id=peer_session.exam_id,
            owner_user_id=peer_session.owner_user_id,
            claimer_user_id=peer_session.claimer_user_id,
        )
        await repository.link_practice_session(
            session,
            peer_session.id,
            practice_session_id=practice_session.id,
            doctor_user_id=practice_session.doctor_user_id,
            patient_user_id=practice_session.patient_user_id,
        )
        peer_session = await repository.peer_session_by_id(session, peer_session_id)
        assert peer_session is not None

    exam_code = await catalog.exam_code_by_id(session, peer_session.exam_id)
    partner = await identity.user_ref_by_id(session, _partner_id(peer_session, user_id))
    return service_reads.session_read(
        peer_session,
        exam_code or "",
        viewer_id=user_id,
        partner_username=service_reads.peer_username(partner),
    )


async def cancel_peer_session(
    session: AsyncSession, peer_session_id: uuid.UUID, *, user_id: uuid.UUID, now: datetime
) -> None:
    """Either person can call off a session that is still scheduled or under way.

    Cancelling one that is already cancelled is refused as `peer_session_not_open`.
    Anyone else is told the session does not exist.
    """
    peer_session = await repository.peer_session_by_id(session, peer_session_id)
    if peer_session is None:
        raise errors.SessionNotFound()
    if user_id not in {peer_session.owner_user_id, peer_session.claimer_user_id}:
        raise errors.SessionNotFound()
    if not await repository.mark_peer_cancelled(session, peer_session_id, at=now):
        raise errors.SessionNotOpen("That session is no longer scheduled or under way.")
