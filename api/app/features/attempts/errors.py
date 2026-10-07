"""The refusals an attempt route can return. Clients branch on each one's `code`."""

from __future__ import annotations

from app.core.errors import Conflict, Forbidden, InvalidInput, NotFound, Unavailable
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
    """No attempt with that id, or it belongs to another organisation."""

    code = "attempt_not_found"
    default_message = "No such attempt"


class AttemptNotReady(Conflict):
    """The worker or the review asked for a definition that has not been rendered yet."""

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
    """The caller is neither the candidate nor an admin allowed to see this attempt."""

    code = "attempt_not_yours"
    default_message = "That attempt belongs to someone else"


class InvalidAttemptState(Conflict):
    """The lifecycle refused the requested move; see `domain.transition`."""

    code = "invalid_attempt_state"
    default_message = "The attempt is not in a state that allows this"


class AttemptInProgress(Conflict):
    """Deleting a station's progress was refused because one attempt at it is
    still mid-consultation. Its own code, because the console says "wait for
    it to end, or fail it" rather than "something went wrong"."""

    code = "attempt_in_progress"
    default_message = "One attempt at this station is still running; end it first"


class UnknownExamError(NotFound):
    """Mirrors `catalog.errors.UnknownExamError`; the code is the shared contract."""

    code = "unknown_exam"
    default_message = "No such exam"


class UserNotFound(NotFound):
    """No such account. The code `tenancy` and `identity` answer with, because
    the console switches on it."""

    code = "user_not_found"
    default_message = "No such account"


class SetEntryAttemptLimitReached(Conflict):
    """Mirrors `station_sets.errors.AttemptLimitReachedError` and shares its code.

    Bootstrap only answers this when a race let two attempts against the same practice-set entry
    both reach the worker at once and the entry's limit was already spent by the first — the
    `station_sets` route that creates an attempt refuses this far earlier, using a count that is
    already stale by the time either attempt starts. Its own class rather than a re-export:
    `station_sets.errors` already imports from this module, and this module importing its class
    back would be a circular import between the two.
    """

    code = "attempt_limit_reached"
    default_message = "You have used every attempt at this station"


class TrialTranscriptInvalid(InvalidInput):
    """A trial mark was given no transcript it could mark: none, both sources, or no candidate turn."""

    code = "invalid_trial_transcript"
    default_message = "Give one transcript to mark, with at least one line the candidate said."


class MarkerUnavailable(Unavailable):
    """The marking engine is not installed or not configured here, so nothing can be marked."""

    code = "marker_unavailable"
    default_message = "Marking is not available on this server."


class AttemptNotReleased(NotFound):
    """An exam slot's candidate asked for its transcript or marks before their result was released.

    The same code as the results slice's refusal: to the candidate it is one rule (R-1).
    """

    code = "result_not_released"
    default_message = "Your result has not been released yet"
