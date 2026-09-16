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
                    can_publish=True,
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
        api = _livekit_api()
        settings = get_settings()
        from livekit.protocol.room import ListParticipantsRequest, RoomParticipantIdentity

        removed = 0
        async with api.LiveKitAPI(
            settings.livekit_url, settings.livekit_api_key, settings.livekit_api_secret
        ) as client:
            listed = await client.room.list_participants(ListParticipantsRequest(room=room))
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

        async with api.LiveKitAPI(
            settings.livekit_url, settings.livekit_api_key, settings.livekit_api_secret
        ) as client:
            await client.agent_dispatch.create_dispatch(
                CreateAgentDispatchRequest(agent_name=agent_name, room=room, metadata=json.dumps(metadata))
            )


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
