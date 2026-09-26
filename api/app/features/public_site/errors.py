from __future__ import annotations

from app.core.errors import InvalidInput, NotFound


class InvalidMessageError(InvalidInput):

    code = "invalid_message"
    default_message = "That message cannot be sent as written"


class MessageNotFound(NotFound):

    code = "message_not_found"
    default_message = "No such message"
