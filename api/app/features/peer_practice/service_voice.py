"""Voice tokens for practice sessions."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ports import VoiceTokens
from app.core.settings import Settings
from app.features.attempts import service as attempts
from app.features.peer_practice import errors, repository_sessions
from app.features.peer_practice.schemas import RoomGrant
from app.features.voice import service as voice


def get_voice_tokens() -> VoiceTokens:
    """The LiveKit adapter, as a FastAPI dependency.

    Imported inside the function so a test can override the dependency
    without the SDK installed, which is the same reason `assistant` does it.
    """
    from app.features.voice.service import get_voice_tokens as build

    return build()


async def voice_grant(
    session: AsyncSession,
    session_id: uuid.UUID,
    *,
    user_id: uuid.UUID,
    tokens: VoiceTokens,
    settings: Settings,
    now: datetime,
) -> RoomGrant:
    """A token for the room two people were paired into.

    The pairing is the permission: both the doctor and the patient join the
    same room and both may speak, so there is no observer shape here. Access is asked again
    here, because a pairing or a booked slot can outlive the trial that paid for it. A
    stranger gets `practice_session_not_found` rather than a refusal, since
    whether a session exists is not something to confirm to somebody not in it.
    """
    practice_session = await repository_sessions.session_by_id(session, session_id)
    if practice_session is None or user_id not in {
        practice_session.doctor_user_id,
        practice_session.patient_user_id,
    }:
        raise errors.SessionNotFound()
    if practice_session.status == "ended" or not practice_session.room_name:
        raise errors.SessionAlreadyEnded()
    # No way into the room until both have accepted: a pairing one side may
    # still decline is not a session yet.
    if practice_session.status == "pending_accept":
        raise errors.NotYetAcceptedError()
    await attempts.require_entitlement(
        session, user_id=user_id, exam_id=practice_session.exam_id, now=now, window_only=True
    )
    granted = voice.grant_for_room(
        room=practice_session.room_name,
        identity=str(user_id),
        can_publish=True,
        tokens=tokens,
        settings=settings,
    )
    return RoomGrant(token=granted.token, server_url=granted.server_url, room=granted.room)
