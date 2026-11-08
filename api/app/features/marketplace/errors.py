"""The refusals a marketplace route can return. Clients branch on each one's `code`."""

from __future__ import annotations

from app.core.errors import Conflict, Forbidden, NotFound


class PostNotFound(NotFound):
    """No slot exists with the given id."""

    code = "post_not_found"
    default_message = "We couldn't find that slot"


class PostUnavailableError(Conflict):
    """Someone else got there first, or the slot is gone.

    409 rather than 404: the caller saw a real slot, and "someone claimed it"
    is a different thing to tell them than "it never existed".
    """

    code = "post_unavailable"
    default_message = "That slot is no longer available"


class SlotAlreadyClaimedError(Conflict):
    """Somebody else claimed the slot in the moment between the caller loading it and pressing claim.

    Its own code, distinct from `post_unavailable`: this is the one refusal
    that resolves itself by showing the next open slot, rather than one that
    means the offer is simply gone (withdrawn, expired, already started).
    """

    code = "slot_already_claimed"
    default_message = "Someone else has already claimed that slot"


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
    default_message = "We couldn't find that session"


class SessionNotOpen(Conflict):
    """The session is cancelled or past its join window."""

    code = "peer_session_not_open"
    default_message = "That session can no longer be joined"


class TooEarlyToJoinError(Conflict):
    """The session's join window has not opened yet.

    Split out from `peer_session_not_open`: a client that gets this back knows
    the session is fine and can say "come back closer to the start time",
    which is a different message to the one for a session that is simply over.
    """

    code = "too_early_to_join"
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
    default_message = "We couldn't find that exam"


# Re-exported, not redefined: offering or claiming a slot runs the same
# entitlement check starting an attempt does, and two classes with one code
# would drift.
from app.features.entitlements.errors import NotEntitled  # noqa: E402

__all__ = ["NotEntitled"]
