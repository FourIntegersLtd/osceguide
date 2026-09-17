from __future__ import annotations

from app.core.errors import Conflict, Forbidden, NotFound
from app.features.entitlements.errors import NotEntitled
from app.features.stations.errors import StationNotPublishedError

# Re-exported so the router can document the refusal without reaching into
# another slice. Deliberately the same class, not a copy: the code is the
# contract and two definitions of it would be free to drift.
#
# `StationNotPublishedError` is T4: bootstrapping an attempt against a station
# still in draft is refused, and the worker route has to declare the code it
# can answer with.
__all__ = ["NotEntitled", "StationNotPublishedError"]


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


class UnknownExamError(NotFound):
    """Mirrors `catalog.errors.UnknownExamError`; the code is the shared contract."""

    code = "unknown_exam"
    default_message = "No such exam"
