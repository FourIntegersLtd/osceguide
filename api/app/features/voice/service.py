"""Issuing a token for an attempt, and deciding which worker will meet it there."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.ports import VoiceTokens
from app.core.settings import Settings
from app.features.attempts import repository as attempts_repo
from app.features.attempts.domain import Status
from app.features.attempts.errors import AttemptNotFound, AttemptNotYours
from app.features.voice import domain, errors
from app.features.voice.schemas import VoiceGrant

log = get_logger(__name__)

# Session types map to the worker family; an attempt kind maps to a session
# type. Kept as a table rather than a chain of ifs so adding a kind is a row.
_SESSION_TYPE_BY_KIND = {
    "practice": "conversation",
    "set_station": "conversation",
    "self_practice": "conversation",
    "exam_slot": "conversation",
    "peer": "conversation",
    "debrief": "debrief",
}


async def grant_for_attempt(
    session: AsyncSession,
    attempt_id: uuid.UUID,
    *,
    requester_id: uuid.UUID,
    tokens: VoiceTokens,
    settings: Settings,
    cloud_slots_free: bool = True,
) -> VoiceGrant:
    attempt = await attempts_repo.attempt_by_id(session, attempt_id)
    if attempt is None:
        raise AttemptNotFound()
    if attempt.user_id != requester_id:
        raise AttemptNotYours()
    if Status(attempt.status) in {Status.EVALUATED, Status.FAILED, Status.INTERACTION_COMPLETE}:
        raise errors.AttemptNotJoinable()
    if not settings.livekit_url:
        raise errors.VoiceUnavailable()

    session_type = _SESSION_TYPE_BY_KIND.get(attempt.kind, "conversation")
    family = domain.family_for(session_type)
    configured = domain.normalize_mode(settings.livekit_routing_mode)
    mode = domain.resolve_mode(configured, cloud_slots_free=cloud_slots_free)
    room = attempt.room_name or domain.room_name_for(str(attempt.id))

    # The three strings the worker is given. Everything else it needs it
    # fetches from the bootstrap route, which is what keeps the dispatch
    # payload from becoming a second, drifting copy of the attempt.
    metadata: dict[str, str] = {
        "attempt_id": str(attempt.id),
        "backend": settings.voice_backend_label,
        "candidate_ref": str(attempt.user_id),
    }

    token = tokens.issue(
        identity=str(attempt.user_id),
        room=room,
        agent_name=domain.agent_name(family, mode),
        dispatch_metadata=metadata,
        ttl_seconds=settings.livekit_token_ttl_seconds,
    )
    return VoiceGrant(token=token, server_url=settings.livekit_url, room=room, attempt_id=attempt.id)


def get_voice_tokens() -> VoiceTokens:
    """The dependency the router wires. Overridden in tests with a recording
    fake, never patched."""
    from app.features.voice.adapter import build_voice_tokens

    return build_voice_tokens()
