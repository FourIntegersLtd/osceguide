"""The LiveKit recorder against a fake LiveKit that behaves like the real one.

Peer recording starts on the server's clock, as the consultation opens, before
either person has joined the room. Real LiveKit refuses to record a room that
does not exist yet, and on staging that refusal failed every session read.
"""

from types import SimpleNamespace

import pytest
from livekit import api as livekit_api

from app.core.settings import get_settings
from app.features.voice import recorder
from app.features.voice.errors import VoiceUnavailable


class FakeLiveKit:
    """Rooms exist only once created; recording a missing room is refused."""

    def __init__(self, *, refuse_everything: bool = False) -> None:
        self.rooms: set[str] = set()
        self.refuse_everything = refuse_everything
        self.room = SimpleNamespace(create_room=self._create_room)
        self.egress = SimpleNamespace(start_room_composite_egress=self._start_egress)

    async def _create_room(self, request: object) -> None:
        """Create a room by name; creating one that exists changes nothing."""
        self.rooms.add(request.name)  # type: ignore[attr-defined]

    async def _start_egress(self, request: object) -> SimpleNamespace:
        """Start recording, refusing as LiveKit does when the room is missing."""
        if self.refuse_everything or request.room_name not in self.rooms:  # type: ignore[attr-defined]
            raise RuntimeError("ServerError(code=not_found, message=requested room does not exist)")
        return SimpleNamespace(egress_id="EG_1")

    async def __aenter__(self) -> "FakeLiveKit":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        return None


@pytest.fixture
def fake_livekit(monkeypatch: pytest.MonkeyPatch) -> FakeLiveKit:
    """Point the recorder at a fake LiveKit, with a bucket and credentials configured."""
    fake = FakeLiveKit()
    settings = get_settings().model_copy(
        update={
            "livekit_url": "wss://example.livekit.cloud",
            "livekit_api_key": "key",
            "livekit_api_secret": "secret",
            "aws_s3_bucket": "recordings",
        }
    )
    monkeypatch.setattr(recorder, "get_settings", lambda: settings)
    monkeypatch.setattr(livekit_api, "LiveKitAPI", lambda *args, **kwargs: fake)
    return fake


async def test_a_room_nobody_has_joined_yet_can_be_recorded(fake_livekit: FakeLiveKit) -> None:
    egress_id = await recorder.LiveKitRecorder().start(
        room="peer-room-1", key="peer_practice/sca/1/consultation.ogg"
    )

    assert egress_id == "EG_1"
    assert fake_livekit.rooms == {"peer-room-1"}


async def test_a_refusal_from_livekit_is_the_ports_own_error(fake_livekit: FakeLiveKit) -> None:
    fake_livekit.refuse_everything = True

    with pytest.raises(VoiceUnavailable, match="LiveKit refused the recording"):
        await recorder.LiveKitRecorder().start(room="peer-room-1", key="peer_practice/sca/1/consultation.ogg")
