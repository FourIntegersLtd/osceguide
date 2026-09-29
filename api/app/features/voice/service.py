"""Issuing a token for an attempt, and deciding which worker will meet it there."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionOpener
from app.core.events import voice_queue_topic
from app.core.logging import get_logger
from app.core.ports import EventBus, RoomAgents, RoomRecorder, VoiceTokens
from app.core.settings import Settings
from app.core.sse import Snapshot, event_stream
from app.features.attempts import service_reads as attempts
from app.features.attempts.errors import AttemptNotFound, AttemptNotYours
from app.features.voice import capacity, domain, errors, seats
from app.features.voice.schemas import CloudCapacityRead, VoiceGrant, VoiceQueueStanding
from app.features.voice.schemas import RoomGrant as RoomGrant

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

# An attempt whose conversation is over cannot be rejoined. Spelled as the
# stored values rather than by importing `attempts.domain`: a slice reaches
# another through its service, and the statuses are part of that contract.
NOT_JOINABLE = frozenset({"interaction_complete", "evaluated", "failed"})


async def grant_for_attempt(
    session: AsyncSession,
    attempt_id: uuid.UUID,
    *,
    requester_id: uuid.UUID,
    tokens: VoiceTokens,
    settings: Settings,
) -> VoiceGrant | VoiceQueueStanding:
    """A token into this attempt's room, with its patient or tutor dispatched to meet it there.

    Seats the room on LiveKit Cloud or our own workers according to the
    configured mode, overflowing to self-hosted when Cloud has no free slot.
    When both are full it returns the candidate's place in line instead of a
    token: a room with no worker free to take it is a patient who never comes.
    """
    attempt = await attempts.attempt_ref(session, attempt_id)
    if attempt is None:
        raise AttemptNotFound()
    if attempt.user_id != requester_id:
        raise AttemptNotYours()
    if attempt.status in NOT_JOINABLE:
        raise errors.AttemptNotJoinable()
    if not settings.livekit_url:
        raise errors.VoiceUnavailable()

    # No default: `domain.family_for` raises on an unknown session type
    # precisely so a patient simulation is never dispatched to the help
    # worker, and defaulting here undid that one layer above it.
    session_type = _SESSION_TYPE_BY_KIND.get(attempt.kind)
    if session_type is None:
        raise errors.VoiceUnavailable(f"No worker family for an attempt of kind {attempt.kind!r}.")
    family = domain.family_for(session_type)
    configured = domain.normalize_mode(settings.livekit_routing_mode)
    room = attempt.room_name or domain.room_name_for(str(attempt.id))

    # A circuit's patient is dispatched by the orchestrator, into a room that
    # is already up. Carrying a dispatch on the candidate's token as well would
    # put a second patient in beside the first, and both would answer. It also
    # takes no seat here: the circuit holds its own when it dispatches, and a
    # Cloud slot taken for a room whose patient runs on our workers would be
    # counted against Cloud for the whole session.
    agent_name: str | None = None
    if attempt.kind != "exam_slot":
        seat = await _seat(settings, room, configured)
        if isinstance(seat, VoiceQueueStanding):
            return seat
        agent_name = domain.agent_name(family, seat, namespace=settings.livekit_agent_namespace)

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
        agent_name=agent_name,
        dispatch_metadata=metadata,
        ttl_seconds=settings.livekit_token_ttl_seconds,
    )
    return VoiceGrant(token=token, server_url=settings.livekit_url, room=room, attempt_id=attempt.id)


async def _seat(settings: Settings, room: str, configured: domain.Mode) -> domain.Mode | VoiceQueueStanding:
    """Where this room's agent will run, or the candidate's place in line when every seat is taken.

    Unmetered Cloud (overflow off) has nothing to count, so it is used as
    configured. Otherwise one atomic admission decides Cloud, our own workers
    or the line, so two replicas can never hand out the same last seat.
    """
    if configured is domain.Mode.LIVEKIT_CLOUD and not settings.livekit_cloud_overflow_enabled:
        return configured
    admission = await seats.admit(settings, room, use_cloud=configured is domain.Mode.LIVEKIT_CLOUD)
    if admission.placement is seats.Placement.QUEUED:
        log.info("every seat is taken; candidate waits in line", room=room, position=admission.position)
        return VoiceQueueStanding(ready=False, position=admission.position)
    on_cloud = admission.placement is seats.Placement.CLOUD
    mode = domain.Mode.LIVEKIT_CLOUD if on_cloud else domain.Mode.SELF_HOSTED
    if mode is not configured:
        log.info("cloud is full; serving from our own workers", room=room)
    return mode


async def ensure_queue_watchable(
    attempt_id: uuid.UUID, *, requester_id: uuid.UUID, open_session: SessionOpener
) -> str:
    """The room whose place in line this person may watch, or raise before the stream opens.

    Checked before the response rather than inside it: a stream that answers
    200 and then dies looks like a network fault rather than a refusal.
    """
    async with open_session() as session:
        attempt = await attempts.attempt_ref(session, attempt_id)
    if attempt is None:
        raise AttemptNotFound()
    if attempt.user_id != requester_id:
        raise AttemptNotYours()
    return attempt.room_name or domain.room_name_for(str(attempt.id))


def queue_stream(room: str, *, settings: Settings, bus: EventBus) -> AsyncIterator[str]:
    """A waiter's place in line, pushed until a seat is theirs to claim.

    Woken when a worker gives a seat back, and re-read on every heartbeat as
    well: a seat whose reservation lapses frees up with nobody announcing it,
    and each read is what keeps this waiter in line. The stream ends on
    `ready`; the page then asks for its token, which takes the seat.
    """
    use_cloud = domain.normalize_mode(settings.livekit_routing_mode) is domain.Mode.LIVEKIT_CLOUD

    async def snapshot() -> Snapshot:
        """The waiter's current standing, final once they may take a seat."""
        place = await seats.standing(settings, room, use_cloud=use_cloud)
        standing = VoiceQueueStanding(ready=place.ready, position=place.position)
        return Snapshot(standing.model_dump_json(), final=standing.ready)

    return event_stream(topics=[voice_queue_topic()], snapshot=snapshot, bus=bus, snapshot_on_heartbeat=True)


def grant_for_room(
    *,
    room: str,
    identity: str,
    can_publish: bool,
    tokens: VoiceTokens,
    settings: Settings,
) -> RoomGrant:
    """A token for a room that already exists, with no agent attached.

    For a caller joining a room somebody else is running — a candidate taking
    their place before the station starts, or an examiner watching one — rather
    than bringing a patient with them, which `grant_for_attempt` does.
    """
    if not settings.livekit_url:
        raise errors.VoiceUnavailable()
    token = tokens.issue(
        identity=identity,
        room=room,
        agent_name=None,
        dispatch_metadata=None,
        can_publish=can_publish,
        ttl_seconds=settings.livekit_token_ttl_seconds,
    )
    return RoomGrant(token=token, server_url=settings.livekit_url, room=room)


async def grant_for_agent_room(
    *,
    room: str,
    session_type: str,
    identity: str,
    dispatch_metadata: dict[str, str],
    tokens: VoiceTokens,
    settings: Settings,
) -> RoomGrant:
    """A token for a room the browser opens, with an agent dispatched into it.

    No recording and no supervisor to dispatch, so the agent rides in on the
    token. `session_type` chooses the family, keeping an assistant session off
    the assessment workers. The caller owns the metadata; this only decides
    where the agent runs.
    """
    if not settings.livekit_url:
        raise errors.VoiceUnavailable()
    family = domain.family_for(session_type)
    configured = domain.normalize_mode(settings.livekit_routing_mode)
    cloud_slots_free = (
        await capacity.slots_free(settings, room) if configured is domain.Mode.LIVEKIT_CLOUD else False
    )
    mode = domain.resolve_mode(configured, cloud_slots_free=cloud_slots_free)
    if mode is not configured:
        log.info("cloud is full; serving from our own workers", room=room, session_type=session_type)

    token = tokens.issue(
        identity=identity,
        room=room,
        agent_name=domain.agent_name(family, mode, namespace=settings.livekit_agent_namespace),
        dispatch_metadata=dispatch_metadata,
        ttl_seconds=settings.livekit_token_ttl_seconds,
    )
    return RoomGrant(token=token, server_url=settings.livekit_url, room=room)


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
    duplicated, contradictory consultation. Returns the agent's name and how
    many stale ones it displaced.
    """
    family = domain.family_for(session_type)
    mode = domain.resolve_mode(domain.normalize_mode(settings.livekit_routing_mode), cloud_slots_free=False)
    agent = domain.agent_name(family, mode, namespace=settings.livekit_agent_namespace)
    # A circuit never waits in line, but its patient occupies one of our seats
    # all the same; left uncounted, the line would admit a candidate into it.
    if family is domain.Family.ASSESSMENT:
        await seats.hold(settings, room)

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


# --- The voice layer as the platform console reads it.


async def cloud_capacity(settings: Settings) -> CloudCapacityRead:
    """The Cloud slot count as the console reads it. Looks; never reserves."""
    active = await capacity.active_slots()
    return CloudCapacityRead(
        overflow_enabled=settings.livekit_cloud_overflow_enabled,
        max_concurrent=settings.livekit_cloud_max_concurrent,
        active=active,
        free=None if active is None else max(0, settings.livekit_cloud_max_concurrent - active),
    )


# --- Recording a room, for the slices that run one.


def get_room_recorder() -> RoomRecorder:
    """The recorder the caller uses. Overridden in tests with a fake."""
    from app.features.voice.recorder import build_room_recorder

    return build_room_recorder()
