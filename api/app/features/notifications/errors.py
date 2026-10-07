"""The refusals the outbox can return. Clients branch on each one's `code`."""

from __future__ import annotations

from app.core.errors import NotFound


class MessageNotRetryable(NotFound):
    """No abandoned message with that id: it was never queued, was sent, or is queued again."""

    code = "message_not_retryable"
    default_message = "That message is not waiting for a retry. Reload the list."
