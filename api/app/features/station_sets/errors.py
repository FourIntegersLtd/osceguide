from __future__ import annotations

from app.core.errors import Conflict, NotFound

# Starting an attempt runs the entitlement check, so `not_entitled` is part of
# this slice's error vocabulary even though the class belongs to `entitlements`.
# Re-exported rather than redefined: two classes with one code would drift, and
# the router documents what it can actually return.
from app.features.attempts.errors import AttemptInProgress, UserNotFound
from app.features.entitlements.errors import NotEntitled

# `AttemptInProgress` and `UserNotFound` are what deleting a station's
# progress can answer, and both belong to `attempts`, which does the deleting.
__all__ = ["AttemptInProgress", "NotEntitled", "UserNotFound"]


class SetNotFound(NotFound):
    code = "set_not_found"
    default_message = "No such practice set"


class EntryNotFound(NotFound):
    code = "set_entry_not_found"
    default_message = "No such station in this set"


class AttemptLimitReachedError(Conflict):
    code = "attempt_limit_reached"
    default_message = "You have used every attempt at this station"


class SetLockedError(Conflict):
    code = "set_locked"
    default_message = "This set is locked because your access has lapsed"


class SetHasAttemptsError(Conflict):
    """A set somebody has run a station in is not only a name and a list.

    Its entries are what those attempts point at, and an attempt is a recording
    and a marking: the schema says so with `RESTRICT`, and with the CHECK that a
    set attempt must name its entry — so the delete cannot be finished by
    nulling a pointer either. Retiring client deleted the session and its
    progress counters and left the transcripts behind, which is the orphan this
    refuses; it does not delete the recordings instead, because that is the
    removal the console asks a reason and an audit row for.
    """

    code = "set_has_attempts"
    default_message = "This set still has attempts recorded against it"


class NothingToDebriefError(Conflict):
    code = "nothing_to_debrief"
    default_message = "Run the station before asking for a debrief"


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


class StationNotFound(NotFound):
    """Mirrors `stations.errors.StationNotFound` and shares its code, for the
    console routes that name a station by id."""

    code = "station_not_found"
    default_message = "No such station"
