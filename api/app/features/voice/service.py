"""Issuing a token for an attempt, and deciding which worker will meet it there."""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.ports import RoomAgents, VoiceTokens
from app.core.settings import Settings
from app.features.attempts import repository as attempts_repo
from app.features.attempts.domain import Status
from app.features.attempts.errors import AttemptNotFound, AttemptNotYours
from app.features.voice import capacity, domain, errors
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
    room = attempt.room_name or domain.room_name_for(str(attempt.id))

    # Asked only when the answer can change the outcome. `slots_free` reserves
    # a slot as it answers — asking and then taking would race — so calling it
    # for a session already routed self-hosted would hold a Cloud slot nobody
    # is going to use until it expired.
    cloud_slots_free = (
        await capacity.slots_free(settings, room) if configured is domain.Mode.LIVEKIT_CLOUD else False
    )
    mode = domain.resolve_mode(configured, cloud_slots_free=cloud_slots_free)
    if mode is not configured:
        log.info("cloud is full; serving from our own workers", room=room, attempt_id=str(attempt.id))

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


# LiveKit propagates a participant removal asynchronously. Dispatching
# immediately after can hand the new agent a room the old one is still leaving,
# and two agents then answer as the patient. b2b waits the same 0.75s.
AGENT_REMOVAL_SETTLE_SECONDS = 0.75


async def dispatch_agent_into_room(
    *,
    agents: RoomAgents,
    settings: Settings,
    room: str,
    attempt_id: uuid.UUID,
    candidate_ref: uuid.UUID,
    session_type: str = "conversation",
    settle_seconds: float = AGENT_REMOVAL_SETTLE_SECONDS,
) -> tuple[str, int]:
    """Put an agent into a room a supervisor is already running (C5).

    Stale agents are removed first and exactly one is dispatched, because two
    agents in a room both answer as the patient and the candidate hears a
    duplicated, contradictory consultation.

    Returns the agent's name and how many stale ones it displaced. The removal
    belongs here rather than at the call site: doing both meant removing twice,
    and the second sweep found nothing while looking like it had worked.

    The metadata is the same three strings the candidate path sends. Everything
    else the worker needs it fetches from the bootstrap route, so this does not
    become a second, drifting copy of the attempt.
    """
    family = domain.family_for(session_type)
    mode = domain.resolve_mode(domain.normalize_mode(settings.livekit_routing_mode), cloud_slots_free=False)
    agent = domain.agent_name(family, mode)

    removed = await agents.remove_agents(room)
    if removed:
        log.info("removed stale agents before dispatch", room=room, removed=removed)
        await asyncio.sleep(settle_seconds)

    await agents.dispatch(
        room=room,
        agent_name=agent,
        metadata={
            "attempt_id": str(attempt_id),
            "backend": settings.voice_backend_label,
            "candidate_ref": str(candidate_ref),
        },
    )
    log.info("dispatched agent", room=room, agent=agent, attempt_id=str(attempt_id))
    return agent, removed


async def clear_agents_from_room(*, agents: RoomAgents, room: str) -> int:
    """Take every agent out of the room. Ends a consultation without ending the circuit."""
    removed = await agents.remove_agents(room)
    log.info("cleared agents from room", room=room, removed=removed)
    return removed


def get_room_agents() -> RoomAgents:
    """The dependency the router wires. Overridden in tests with a fake."""
    from app.features.voice.adapter import build_room_agents

    return build_room_agents()
