from __future__ import annotations

from app.core.errors import Conflict, Forbidden, NotFound
from app.features.entitlements.errors import NotEntitled
from app.features.stations.errors import StationNotFound, StationNotPublishedError

# Re-exported so the router can document the refusal without reaching into
# another slice. Deliberately the same class, not a copy: the code is the
# contract and two definitions of it would be free to drift.
#
# `StationNotPublishedError` is T4: bootstrapping an attempt against a station
# still in draft is refused, and the worker route has to declare the code it
# can answer with.
# `StationNotFound` is how creation answers a station version that does not
# exist or belongs to another organisation. The two are one refusal on
# purpose: "no such station" and "not yours" must not be distinguishable,
# or the route becomes a way to enumerate another tenant's library.
__all__ = ["NotEntitled", "StationNotFound", "StationNotPublishedError"]


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


class AttemptNotFinished(Conflict):
    """The review was asked for while the consultation was still to come.

    A separate code from `invalid_attempt_state` because the client acts on it:
    the review tab is offered as soon as the station is open and must say "not
    yet" rather than "something went wrong".
    """

    code = "attempt_not_finished"
    default_message = "This attempt has not finished, so there is nothing to review yet"


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
