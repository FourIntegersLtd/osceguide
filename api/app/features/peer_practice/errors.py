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
