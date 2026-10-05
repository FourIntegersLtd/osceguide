"""The status values a media item's AV production job moves through, from the moment a
platform admin asks for its facts or script to be checked, or for narrated slides or a podcast,
to the moment the file is ready.
"""

from __future__ import annotations

GENERATING_AUDIO = "generating_audio"
GENERATING_VIDEO = "generating_video"
GENERATING_PODCAST = "generating_podcast"
CHECKING_FACTS = "checking_facts"
WRITING_SCRIPT = "writing_script"
# The agent is drafting, checking and correcting the item on its own.
PRODUCING = "producing"
# The script is written and checked, and waits for a person to read it before it is voiced.
AWAITING_REVIEW = "awaiting_review"
COMPLETED = "completed"
FAILED = "failed"

RUNNING = frozenset(
    {GENERATING_AUDIO, GENERATING_VIDEO, GENERATING_PODCAST, CHECKING_FACTS, WRITING_SCRIPT, PRODUCING}
)


def is_running(status: str | None) -> bool:
    """Whether a production job is still in flight for this status, so a caller knows to keep waiting."""
    return (status or "") in RUNNING
