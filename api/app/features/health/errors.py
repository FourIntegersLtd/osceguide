"""The errors this slice's routes declare. Each `code` is a contract clients branch on, never `message`."""

from __future__ import annotations

from app.core.errors import Conflict, NotFound


class MessageNotRetryable(NotFound):
    """No abandoned message with that id: it was never queued, was sent, or is queued again."""

    code = "message_not_retryable"
    default_message = "That message is not waiting for a retry. Reload the list."


class JobNotFound(NotFound):
    """No background task with that id."""

    code = "job_not_found"
    default_message = "That background task does not exist. Reload the list."


class JobNotRetryable(Conflict):
    """Only a failed task that is not a marking can be queued again from here."""

    code = "job_not_retryable"
    default_message = "That task cannot be retried here. A failed marking is retried from its attempt."


class JobNotCancellable(Conflict):
    """Only a waiting task, or a running one whose worker has gone quiet, can be cancelled."""

    code = "job_not_cancellable"
    default_message = "That task is running normally, so it cannot be cancelled. Reload the list."
