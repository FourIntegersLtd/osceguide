"""The refusals an AV production route can return. Clients branch on each one's `code`."""

from __future__ import annotations

from app.core.errors import AppError, Conflict, InvalidInput


class AvUnavailable(AppError):
    """Raised when the storage or narration providers a production job needs are not configured."""

    code = "av_unavailable"
    default_message = "Audio/video production is not configured on this environment"


class AvAlreadyRunning(Conflict):
    """Raised when a new production job is requested while one is already running for this item."""

    code = "av_already_running"
    default_message = "Production is already in progress for this item"


class WrongMediaKind(InvalidInput):
    """Raised when a production operation is asked for on a kind of item it does not apply to,
    such as narrating a blog post.
    """

    code = "media_wrong_kind"
    default_message = "That operation does not apply to this kind of study material"


from app.features.media.errors import ItemNotFound  # noqa: E402

__all__ = ["AvUnavailable", "AvAlreadyRunning", "WrongMediaKind", "ItemNotFound"]
