from __future__ import annotations

from app.core.errors import Conflict, Forbidden, NotFound


class AttemptNotFound(NotFound):
    code = "attempt_not_found"
    default_message = "No such attempt"


class AttemptNotReady(Conflict):
    code = "attempt_not_ready"
    default_message = "This attempt has no rendered definition yet"


class AttemptMismatch(Conflict):
    """The body names a different attempt than the path.

    A worker is dispatched for exactly one attempt and is given nothing else,
    so this means a bug or a misrouted job, not a user error.
    """

    code = "attempt_mismatch"
    default_message = "That payload belongs to a different attempt"


class AttemptNotYours(Forbidden):
    code = "attempt_not_yours"
    default_message = "That attempt belongs to someone else"


class InvalidAttemptState(Conflict):
    code = "invalid_attempt_state"
    default_message = "The attempt is not in a state that allows this"
