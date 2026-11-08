"""The refusals a public-site route can return. Clients branch on each one's `code`."""

from __future__ import annotations

from app.core.errors import Conflict, InvalidInput, NotFound


class InvalidMessageError(InvalidInput):
    """A contact or feedback message that fails the sending rules, such as a missing email address."""

    code = "invalid_message"
    default_message = "That message cannot be sent as written"


class MessageNotFound(NotFound):
    """No such site message. Used when marking a message handled by an id that does not exist."""

    code = "message_not_found"
    default_message = "We couldn't find that message"


class CannotReplyInApp(Conflict):
    """The sender was not signed in, so there is no inbox to reply into."""

    code = "message_not_repliable"
    default_message = "That message was sent without signing in; reply by email"
