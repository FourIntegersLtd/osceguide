"""The status values a media item's AV production job moves through, from the moment a
platform admin asks for narrated slides or a podcast to the moment the file is ready.
"""

from __future__ import annotations

GENERATING_AUDIO = "generating_audio"
GENERATING_VIDEO = "generating_video"
GENERATING_PODCAST = "generating_podcast"
COMPLETED = "completed"
FAILED = "failed"

RUNNING = frozenset({GENERATING_AUDIO, GENERATING_VIDEO, GENERATING_PODCAST})


def is_running(status: str | None) -> bool:
    """Whether a production job is still in flight for this status, so a caller knows to poll again."""
    return (status or "") in RUNNING
