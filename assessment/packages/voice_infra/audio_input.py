"""Room audio input for voice workers."""

from __future__ import annotations

from livekit.agents import room_io
from livekit.plugins import noise_cancellation

# WebRTC mic tracks are typically 48 kHz. RoomOptions audio defaults to 24 kHz,
# which makes Krisp NC abort on Linux (input and output sample rates must match).
_AUDIO_SAMPLE_RATE = 48000


def build_room_options(**kwargs: object) -> room_io.RoomOptions:
    """Room options with noise cancellation on the audio input; extra keyword arguments pass through."""
    return room_io.RoomOptions(
        audio_input=room_io.AudioInputOptions(noise_cancellation=noise_cancellation.NC(), sample_rate=_AUDIO_SAMPLE_RATE),
        **kwargs,
    )
