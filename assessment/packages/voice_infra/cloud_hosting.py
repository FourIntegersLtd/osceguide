"""Where this worker runs: the one reader of ``OSCE_LIVEKIT_HOSTING``."""

from __future__ import annotations

import os


def is_livekit_cloud() -> bool:
    """True on a LiveKit Cloud agent: ``OSCE_LIVEKIT_HOSTING`` is ``cloud`` or ``livekit-cloud``."""
    return (os.getenv("OSCE_LIVEKIT_HOSTING") or "").strip().lower() in {"cloud", "livekit-cloud"}
