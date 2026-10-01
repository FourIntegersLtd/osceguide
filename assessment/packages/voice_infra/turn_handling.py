"""Turn-handling presets for voice workers."""

from __future__ import annotations

import os
from typing import Literal

from livekit.agents import TurnHandlingOptions
from livekit.agents.inference import TurnDetector

MIN_CONSECUTIVE_SPEECH_DELAY = 0.45

TurnDetectorVersion = Literal["v1", "v1-mini"]


def turn_detector_version() -> TurnDetectorVersion:
    """Cloud-hosted agents use Inference ``v1``; everything else the on-box ``v1-mini``.

    Hosting is declared by ``OSCE_LIVEKIT_HOSTING``: ``cloud`` for LiveKit Cloud,
    ``self-hosted`` for on-box turn detection.
    """
    hosting = (os.getenv("OSCE_LIVEKIT_HOSTING") or "").strip().lower()
    if hosting == "self-hosted":
        return "v1-mini"
    if hosting in {"cloud", "livekit-cloud"}:
        return "v1"
    return "v1-mini"


def build_turn_handling_options(*, preemptive: bool = False, max_endpoint_delay: float = 1.8) -> TurnHandlingOptions:
    """Build the turn detection, endpointing and interruption settings for a voice session."""
    return TurnHandlingOptions(
        turn_detection=TurnDetector(version=turn_detector_version()),
        endpointing={"mode": "dynamic", "min_delay": 0.5, "max_delay": max_endpoint_delay, "alpha": 0.82},
        interruption={
            "mode": "adaptive",
            "min_duration": 0.45,
            "min_words": 1,
            "enabled": True,
            "discard_audio_if_uninterruptible": False,
            "false_interruption_timeout": 1.5,
            "resume_false_interruption": False,
            "backchannel_boundary": (1.0, 3.5),
        },
        preemptive_generation={"enabled": preemptive},
    )
