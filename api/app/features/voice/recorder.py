"""The LiveKit implementation of the recording port. The SDK is imported inside
the functions, so the API starts and tests run without it installed.

Audio only: a recording exists to be transcribed and marked, and a video
composite costs more to encode and store for nothing that is ever read back.
"""

from __future__ import annotations

from typing import Any

from app.core.settings import Settings, get_settings
from app.features.voice.errors import VoiceUnavailable


class LiveKitRecorder:
    """Records a room to the bucket `media_production` already writes to."""

    async def start(self, *, room: str, key: str) -> str:
        """Start a room's audio-only recording to this storage key, returning its egress id."""
        api = _livekit_api()
        settings = get_settings()
        _require_bucket(settings)
        request = api.RoomCompositeEgressRequest(
            room_name=room,
            audio_only=True,
            file_outputs=[
                api.EncodedFileOutput(
                    # LiveKit writes the object itself, so the credentials
                    # travel with the request rather than being used here.
                    filepath=key,
                    s3=api.S3Upload(
                        bucket=settings.aws_s3_bucket,
                        region=settings.aws_region,
                        access_key=settings.aws_access_key_id,
                        secret=settings.aws_secret_access_key,
                        force_path_style=False,
                    ),
                )
            ],
        )
        from livekit.protocol.room import CreateRoomRequest

        async with api.LiveKitAPI(
            settings.livekit_url, settings.livekit_api_key, settings.livekit_api_secret
        ) as client:
            try:
                # Created first: recording starts on the server's clock, as the
                # consultation opens, before either person has joined, and
                # LiveKit refuses to record a room that does not exist yet.
                # Creating an existing room is a no-op.
                await client.room.create_room(CreateRoomRequest(name=room))
                started = await client.egress.start_room_composite_egress(request)
            except Exception as exc:  # noqa: BLE001 - one transport error type for every condition
                # Surfaced as the port's own error, so the caller records the
                # session as unrecorded rather than failing the request.
                raise VoiceUnavailable(f"LiveKit refused the recording: {exc}") from exc
        egress_id = getattr(started, "egress_id", "")
        if not egress_id:
            # Without an id there is no way to stop it later, and a recording
            # that cannot be stopped runs until the room is reaped.
            raise VoiceUnavailable("LiveKit accepted the recording but returned no egress id")
        return str(egress_id)

    async def stop(self, *, egress_id: str) -> None:
        """Stop this recording, treating one that already ended on its own as success."""
        api = _livekit_api()
        settings = get_settings()
        async with api.LiveKitAPI(
            settings.livekit_url, settings.livekit_api_key, settings.livekit_api_secret
        ) as client:
            try:
                await client.egress.stop_egress(api.StopEgressRequest(egress_id=egress_id))
            except Exception as exc:  # noqa: BLE001 - one transport error type for every condition
                # An egress that ended on its own — the room emptied, the
                # encoder finished — is already stopped. Asking again is how a
                # retry looks, and the outcome wanted is the one already true.
                if _already_finished(exc):
                    return
                raise


def _already_finished(exc: Exception) -> bool:
    """Whether stopping failed because there was nothing left to stop."""
    message = str(exc).lower()
    return "not_found" in message or "already" in message or "egress_complete" in message


def _require_bucket(settings: Settings) -> None:
    """Raise unless storage credentials are configured to record with."""
    if not (settings.aws_access_key_id and settings.aws_secret_access_key):
        raise VoiceUnavailable("No S3 credentials are configured, so there is nowhere to record to")


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


def build_room_recorder() -> LiveKitRecorder:
    """The dependency this slice wires for recording a room to storage."""
    return LiveKitRecorder()
