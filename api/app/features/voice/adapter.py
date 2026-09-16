"""The LiveKit implementation of the token port.

Imported lazily so the SDK is not required to run tests or to start the API
without voice configured.
"""

from __future__ import annotations

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
