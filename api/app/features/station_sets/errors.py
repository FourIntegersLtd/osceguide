from __future__ import annotations

from app.core.errors import Conflict, NotFound

# Starting an attempt runs the entitlement check, so `not_entitled` is part of
# this slice's error vocabulary even though the class belongs to `entitlements`.
# Re-exported rather than redefined: two classes with one code would drift, and
# the router documents what it can actually return.
from app.features.entitlements.errors import NotEntitled

__all__ = ["NotEntitled"]


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
