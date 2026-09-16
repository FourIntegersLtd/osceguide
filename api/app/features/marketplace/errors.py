from __future__ import annotations

from app.core.errors import Conflict, Forbidden, NotFound


class PostNotFound(NotFound):
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
    code = "cannot_claim_own_post"
    default_message = "You cannot claim your own slot"


class NotYoursError(Forbidden):
    code = "not_your_post"
    default_message = "Only the person who offered a slot can withdraw it"


class SessionNotFound(NotFound):
    code = "peer_session_not_found"
    default_message = "No such session"


class SessionNotOpen(Conflict):
    code = "peer_session_not_open"
    default_message = "That session has not opened yet"
