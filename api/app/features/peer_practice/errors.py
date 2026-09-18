from __future__ import annotations

from app.core.errors import Conflict, NotFound


class QueueEntryNotFound(NotFound):
    code = "queue_entry_not_found"
    default_message = "You are not in the queue"


class SessionNotFound(NotFound):
    code = "practice_session_not_found"
    default_message = "No such practice session"


class AlreadyQueued(Conflict):
    """Joining twice keeps the place you already have.

    409 with the existing entry rather than a second place in the line.
    """

    code = "already_queued"
    default_message = "You are already waiting"


class SessionAlreadyEnded(Conflict):
    code = "practice_session_ended"
    default_message = "That session has already finished"


class UnknownExamError(NotFound):
    """Mirrors `catalog.errors.UnknownExamError`, and shares its code.

    Declared here so this slice's routes can document the refusal without
    importing another slice's error class into their signatures — the same
    reason `stations` and `attempts` mirror it. It became reachable in
    practice once exams stopped being four seeded rows: a code that names no
    published exam is now an ordinary thing for a client to send.
    """

    code = "unknown_exam"
    default_message = "No such exam"


# Re-exported, not copied: the code is the contract, and `voice` owns it.
from app.features.voice.errors import VoiceUnavailable  # noqa: E402

__all__ = [
    "AlreadyQueued",
    "QueueEntryNotFound",
    "SessionAlreadyEnded",
    "SessionNotFound",
    "UnknownExamError",
    "VoiceUnavailable",
]
