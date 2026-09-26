"""The refusals a marketplace route can return. Clients branch on each one's `code`."""

from __future__ import annotations

from app.core.errors import Conflict, Forbidden, NotFound


class PostNotFound(NotFound):
    """No slot exists with the given id."""

    code = "post_not_found"
    default_message = "No such slot"


class PostUnavailableError(Conflict):
    """Someone else got there first, or the slot is gone.

    409 rather than 404: the caller saw a real slot, and "someone claimed it"
    is a different thing to tell them than "it never existed".
    """

    code = "post_unavailable"
    default_message = "That slot is no longer available"


class CannotClaimOwnPostError(Conflict):
    """The caller tried to claim the slot they offered themselves."""

    code = "cannot_claim_own_post"
    default_message = "You cannot claim your own slot"


class NotYoursError(Forbidden):
    """Someone other than the person who offered a slot tried to withdraw it."""

    code = "not_your_post"
    default_message = "Only the person who offered a slot can withdraw it"


class SessionNotFound(NotFound):
    """No booked session exists with the given id."""

    code = "peer_session_not_found"
    default_message = "No such session"


class SessionNotOpen(Conflict):
    """The session is cancelled, not yet open, or past its join window."""

    code = "peer_session_not_open"
    default_message = "That session has not opened yet"


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


# Re-exported, not redefined: offering or claiming a slot runs the same
# entitlement check starting an attempt does, and two classes with one code
# would drift.
from app.features.entitlements.errors import NotEntitled  # noqa: E402

__all__ = ["NotEntitled"]
