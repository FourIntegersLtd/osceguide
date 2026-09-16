from __future__ import annotations

from app.core.errors import Conflict, NotFound


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
