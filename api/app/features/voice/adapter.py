"""The LiveKit implementation of the token port.

Imported lazily so the SDK is not required to run tests or to start the API
without voice configured.
"""

from __future__ import annotations

from typing import Any

from app.core.ports import VoiceTokens
from app.core.settings import get_settings
from app.features.voice.errors import VoiceUnavailable


class LiveKitTokens:
    def issue(
        self,
        *,
        identity: str,
        room: str,
        agent_name: str | None,
        dispatch_metadata: dict[str, str] | None,
        room_admin: bool = False,
        can_publish: bool = True,
        ttl_seconds: int = 3600,
    ) -> str:
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
            .with_name(identity)
            .with_ttl(timedelta(seconds=ttl_seconds))
            .with_grants(
                api.VideoGrants(
                    room_join=True,
                    room=room,
                    can_publish=can_publish,
                    # Defaults to true, which would let an observer type into
                    # the room's data channel. Watch and listen means neither.
                    can_publish_data=can_publish,
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

        LiveKit answers `not_found` for a room nobody has joined yet, and that
        used to fail the whole call. On exam day the consequence was a stalled
        circuit: the reading phase ends, the transition tries to dispatch the
        patient, the candidate's browser has not opened the room yet, and the
        scheduled job errors instead of advancing. The circuit then sits
        overdue for ever, because every retry hits the same empty room.

        Nothing to remove is success.
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
                if not isinstance(identity, str) or not identity.startswith("agent-"):
                    continue
                await client.room.remove_participant(RoomParticipantIdentity(room=room, identity=identity))
                removed += 1
        return removed

    async def dispatch(self, *, room: str, agent_name: str, metadata: dict[str, str]) -> None:
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


def _is_room_missing(exc: Exception) -> bool:
    """Whether a LiveKit error means "no such room" rather than a real fault.

    Matched on the message because the SDK raises one transport error type for
    every server-side condition, so catching the class alone would swallow an
    authentication failure too.
    """
    return "not_found" in str(exc) or "does not exist" in str(exc)


def _livekit_api() -> Any:
    settings = get_settings()
    if not (settings.livekit_url and settings.livekit_api_key and settings.livekit_api_secret):
        raise VoiceUnavailable("LiveKit credentials are not configured")
    try:
        from livekit import api
    except ImportError as exc:  # pragma: no cover - depends on deployment extras
        raise VoiceUnavailable("The LiveKit SDK is not installed") from exc
    return api


def build_room_agents() -> LiveKitRoomAgents:
    return LiveKitRoomAgents()
