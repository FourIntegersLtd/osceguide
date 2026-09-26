"""The refusals a peer-practice route can return. Clients branch on each one's `code`."""

from __future__ import annotations

from app.core.errors import Conflict, NotFound


class QueueEntryNotFound(NotFound):
    """This queue place is not this caller's, or has already gone."""

    code = "queue_entry_not_found"
    default_message = "You are not in the queue"


class SessionNotFound(NotFound):
    """No such practice session, or the caller was not one of its pair."""

    code = "practice_session_not_found"
    default_message = "No such practice session"


class AlreadyQueued(Conflict):
    """Joining twice keeps the place you already have.

    409 with the existing entry rather than a second place in the line.
    """

    code = "already_queued"
    default_message = "You are already waiting"


class SessionAlreadyEnded(Conflict):
    """The session this call would act on has already finished."""

    code = "practice_session_ended"
    default_message = "That session has already finished"


class UnknownExamError(NotFound):
    """Mirrors `catalog.errors.UnknownExamError` and shares its code, so this
    slice's routes can document the refusal without importing another
    slice's error class into their signatures.
    """

    code = "unknown_exam"
    default_message = "No such exam"


# Re-exported, not copied: the code is the contract, and the slice named owns
# it. Queueing for a peer session runs the same entitlement check starting an
# attempt does, so `not_entitled` is part of this slice's vocabulary.
from app.features.entitlements.errors import NotEntitled  # noqa: E402
from app.features.voice.errors import VoiceUnavailable  # noqa: E402

__all__ = [
    "AlreadyQueued",
    "NotEntitled",
    "QueueEntryNotFound",
    "SessionAlreadyEnded",
    "SessionNotFound",
    "UnknownExamError",
    "VoiceUnavailable",
]
