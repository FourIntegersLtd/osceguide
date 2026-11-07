"""The LiveKit implementation of the token port.

Imported lazily so the SDK is not required to run tests or to start the API
without voice configured.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.core.logging import get_logger
from app.core.ports import AGENT_PREFIX, VoiceTokens
from app.core.settings import get_settings
from app.features.voice.errors import VoiceUnavailable

log = get_logger(__name__)


class LiveKitTokens:
    """Mints LiveKit access tokens, dispatching an agent alongside the candidate when named."""

    def issue(
        self,
        *,
        identity: str,
        room: str,
        agent_name: str | None,
        dispatch_metadata: dict[str, str] | None,
        room_admin: bool = False,
        can_publish: bool = True,
        can_publish_sources: list[str] | None = None,
        ttl_seconds: int = 3600,
        display_name: str | None = None,
    ) -> str:
        """A signed JWT granting this identity access to the room, with an agent dispatch if named."""
        import json
        from datetime import timedelta

        try:
            from livekit import api
        except ImportError as exc:  # pragma: no cover - depends on deployment extras
            raise VoiceUnavailable("The LiveKit SDK is not installed") from exc

        settings = get_settings()
        if not (settings.livekit_api_key and settings.livekit_api_secret):
            raise VoiceUnavailable("LiveKit credentials are not configured")

        token = (
            api.AccessToken(api_key=settings.livekit_api_key, api_secret=settings.livekit_api_secret)
            .with_identity(identity)
            .with_name(display_name or identity)
            .with_ttl(timedelta(seconds=ttl_seconds))
            .with_grants(
                api.VideoGrants(
                    room_join=True,
                    room=room,
                    can_publish=can_publish,
                    # Defaults to true, which would let an observer type into
                    # the room's data channel. Watch and listen means neither.
                    can_publish_data=can_publish,
                    can_publish_sources=can_publish_sources,
                    can_subscribe=True,
                    room_admin=room_admin,
                )
            )
        )
        if agent_name:
            # Dispatch rides on the candidate's own token, so the agent joins
            # when they do rather than waiting in an empty room.
            token = token.with_room_config(
                api.RoomConfiguration(
                    agents=[
                        api.RoomAgentDispatch(
                            agent_name=agent_name, metadata=json.dumps(dispatch_metadata or {})
                        )
                    ]
                )
            )
        return str(token.to_jwt())


def build_voice_tokens() -> VoiceTokens:
    return LiveKitTokens()


class LiveKitRoomAgents:
    """Explicit agent dispatch, for rooms a supervisor is already running."""

    async def remove_agents(self, room: str) -> int:
        """Clear stale patients out of a room. A room that does not exist has none.

        LiveKit answers `not_found` for a room nobody has joined yet; treating that
        as a failure once stalled a circuit whose candidate had not opened the room
        yet, since every retry hit the same empty room. Nothing to remove is success.
        """
        api = _livekit_api()
        settings = get_settings()
        from livekit.protocol.room import ListParticipantsRequest, RoomParticipantIdentity

        removed = 0
        async with api.LiveKitAPI(
            settings.livekit_url, settings.livekit_api_key, settings.livekit_api_secret
        ) as client:
            try:
                listed = await client.room.list_participants(ListParticipantsRequest(room=room))
            except Exception as exc:  # noqa: BLE001 - the SDK raises a transport error type
                if _is_room_missing(exc):
                    return 0
                raise
            for participant in listed.participants:
                identity = getattr(participant, "identity", "")
                # LiveKit names agent participants `agent-*`; a candidate or a
                # supervisor must never be removed by this.
                if not isinstance(identity, str) or not identity.startswith(AGENT_PREFIX):
                    continue
                try:
                    await client.room.remove_participant(
                        RoomParticipantIdentity(room=room, identity=identity)
                    )
                except Exception as exc:  # noqa: BLE001 - as above
                    # The last participant can leave between the list and this
                    # call, and LiveKit reaps an empty room. Same outcome as an
                    # absent agent, so it is not a failure either.
                    if _is_room_missing(exc):
                        continue
                    raise
                removed += 1
        return removed

    async def close_room(self, room: str, *, force: bool = False) -> bool:
        """Delete the room once its agent is in it, so the agent leaves now instead of after LiveKit's
        empty-room timeout. Returns whether it was deleted.

        Only once an agent has joined: a worker still starting up when its room
        is deleted never connects, never shuts down, and so never releases its
        seat (seen locally with a cold worker). Left alone, that room closes on
        LiveKit's timeout after the agent has joined, as it always did.

        A room that is already gone is the outcome asked for, so it is not a
        failure: LiveKit reaps an empty room on its own.

        `force` skips the agent check: a supervisor closing a training room after End, when
        the patient has already left and everyone else must be disconnected.
        """
        api = _livekit_api()
        settings = get_settings()
        from livekit.protocol.room import DeleteRoomRequest, ListParticipantsRequest

        async with api.LiveKitAPI(
            settings.livekit_url, settings.livekit_api_key, settings.livekit_api_secret
        ) as client:
            try:
                listed = await client.room.list_participants(ListParticipantsRequest(room=room))
                # LiveKit names agent participants `agent-*`, as `remove_agents` relies on.
                if not force and not any(
                    str(getattr(participant, "identity", "")).startswith(AGENT_PREFIX)
                    for participant in listed.participants
                ):
                    return False
                await client.room.delete_room(DeleteRoomRequest(room=room))
            except Exception as exc:  # noqa: BLE001 - the SDK raises a transport error type
                if _is_room_missing(exc):
                    return False
                raise
        return True

    async def set_mic_permissions(self, room: str, may_speak: Callable[[str], bool]) -> None:
        """Apply `may_speak` to everyone in the room who is not an agent; an empty room has no one.

        One person failing (they left between the list and the update) does not stop the rest.
        """

        async def apply(client: Any, participant: Any) -> None:
            """Give one person the microphone the rule allows; a person who just left is skipped."""
            identity = str(getattr(participant, "identity", ""))
            if identity.startswith(AGENT_PREFIX):
                return
            try:
                await _apply_mic(client, room, participant, may_speak(identity))
            except Exception:  # noqa: BLE001 - the SDK raises a transport error type
                log.warning("could not set one microphone", room=room, identity=identity, exc_info=True)

        await _for_participants(room, apply)

    async def set_mic_permission(self, room: str, identity: str, allowed: bool) -> None:
        """The same for one person; nothing to do if they are not in the room now."""

        async def apply(client: Any, participant: Any) -> None:
            """Switch this one person's microphone when they are the one asked about."""
            if str(getattr(participant, "identity", "")) == identity:
                await _apply_mic(client, room, participant, allowed)

        await _for_participants(room, apply)

    async def dispatch(self, *, room: str, agent_name: str, metadata: dict[str, str]) -> None:
        """Create the room if it does not exist yet, then explicitly dispatch this agent into it."""
        import json

        api = _livekit_api()
        settings = get_settings()
        from livekit.protocol.agent_dispatch import CreateAgentDispatchRequest
        from livekit.protocol.room import CreateRoomRequest

        async with api.LiveKitAPI(
            settings.livekit_url, settings.livekit_api_key, settings.livekit_api_secret
        ) as client:
            # Created first, because a circuit dispatches its patient on the
            # server's clock rather than when somebody joins: at that moment
            # the room may not exist yet. Creating an existing room is a no-op.
            await client.room.create_room(CreateRoomRequest(name=room))
            await client.agent_dispatch.create_dispatch(
                CreateAgentDispatchRequest(agent_name=agent_name, room=room, metadata=json.dumps(metadata))
            )


async def _for_participants(room: str, apply: Callable[[Any, Any], Awaitable[None]]) -> None:
    """Call `apply(client, participant)` for everyone in the room; a room that is gone has no one."""
    api = _livekit_api()
    settings = get_settings()
    from livekit.protocol.room import ListParticipantsRequest

    async with api.LiveKitAPI(
        settings.livekit_url, settings.livekit_api_key, settings.livekit_api_secret
    ) as client:
        try:
            listed = await client.room.list_participants(ListParticipantsRequest(room=room))
        except Exception as exc:  # noqa: BLE001 - the SDK raises a transport error type
            if _is_room_missing(exc):
                return
            raise
        for participant in listed.participants:
            await apply(client, participant)


async def _apply_mic(client: Any, room: str, participant: Any, allowed: bool) -> None:
    """Set a participant's publish sources to camera plus, if allowed, microphone.

    The permission is enforced by LiveKit, so a browser cannot publish a microphone it was not given.
    A microphone already published is muted too, because revoking the permission alone does not stop it.
    """
    from livekit.protocol.models import ParticipantPermission, TrackSource, TrackType
    from livekit.protocol.room import MuteRoomTrackRequest, UpdateParticipantRequest

    sources = [TrackSource.CAMERA] + ([TrackSource.MICROPHONE] if allowed else [])
    base = participant.permission
    permission = ParticipantPermission(
        can_subscribe=True,
        can_publish=True,
        can_publish_data=base.can_publish_data if base is not None else True,
        can_publish_sources=sources,
    )
    await client.room.update_participant(
        UpdateParticipantRequest(room=room, identity=participant.identity, permission=permission)
    )
    if allowed:
        return
    for track in participant.tracks:
        if track.type == TrackType.AUDIO and track.source == TrackSource.MICROPHONE and not track.muted:
            await client.room.mute_published_track(
                MuteRoomTrackRequest(
                    room=room, identity=participant.identity, track_sid=track.sid, muted=True
                )
            )


def _is_room_missing(exc: Exception) -> bool:
    """Whether a LiveKit error means "no such room" rather than a real fault.

    Matched on the message because the SDK raises one transport error type for
    every server-side condition, so catching the class alone would swallow an
    authentication failure too.
    """
    return "not_found" in str(exc) or "does not exist" in str(exc)


def _livekit_api() -> Any:
    """The `livekit.api` module, or raise `VoiceUnavailable` if it cannot be used."""
    settings = get_settings()
    if not (settings.livekit_url and settings.livekit_api_key and settings.livekit_api_secret):
        raise VoiceUnavailable("LiveKit credentials are not configured")
    try:
        from livekit import api
    except ImportError as exc:  # pragma: no cover - depends on deployment extras
        raise VoiceUnavailable("The LiveKit SDK is not installed") from exc
    return api


def build_room_agents() -> LiveKitRoomAgents:
    """The dependency this slice's router and service wire for explicit agent dispatch."""
    return LiveKitRoomAgents()
