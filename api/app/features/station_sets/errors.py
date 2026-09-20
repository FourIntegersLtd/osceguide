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
