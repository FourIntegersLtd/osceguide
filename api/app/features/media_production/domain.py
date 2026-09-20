from __future__ import annotations

GENERATING_AUDIO = "generating_audio"
GENERATING_VIDEO = "generating_video"
GENERATING_PODCAST = "generating_podcast"
COMPLETED = "completed"
FAILED = "failed"

RUNNING = frozenset({GENERATING_AUDIO, GENERATING_VIDEO, GENERATING_PODCAST})


def is_running(status: str | None) -> bool:
    return (status or "") in RUNNING
