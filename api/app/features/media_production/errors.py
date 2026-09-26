from __future__ import annotations

from app.core.errors import AppError, Conflict, InvalidInput


class AvUnavailable(AppError):

    code = "av_unavailable"
    default_message = "Audio/video production is not configured on this environment"


class AvAlreadyRunning(Conflict):

    code = "av_already_running"
    default_message = "Production is already in progress for this item"


class WrongMediaKind(InvalidInput):

    code = "media_wrong_kind"
    default_message = "That operation does not apply to this kind of study material"


from app.features.media.errors import ItemNotFound  # noqa: E402

__all__ = ["AvUnavailable", "AvAlreadyRunning", "WrongMediaKind", "ItemNotFound"]
