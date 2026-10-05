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


class ClaimOutsideItem(InvalidInput):
    """Raised when a hand check places a claim on a slide the item does not have."""

    code = "claim_outside_item"
    default_message = "A claim names a slide this item does not have"


class ScriptNotChecked(Conflict):
    """Raised when voicing is asked for words that have not been checked, or were edited since."""

    code = "script_not_checked"
    default_message = "Write and check the script before voicing it"


class StationHasNoTemplate(Conflict):
    """Raised when the agent is asked to produce a station that has no template to draft it in."""

    code = "station_has_no_template"
    default_message = "This station has no template, so it cannot be drafted"


# Refusals of other slices that this slice's routes answer, so the router documents them from here.
from app.features.media.errors import ItemNotFound, NotEditableError  # noqa: E402
from app.features.stations.errors import (  # noqa: E402
    FactCheckRunning,
    StationBeingProduced,
    StationNotFound,
    VersionNotFound,
)
from app.features.stations.errors import NotEditableError as StationNotEditable  # noqa: E402

__all__ = [
    "AvUnavailable",
    "AvAlreadyRunning",
    "WrongMediaKind",
    "ScriptNotChecked",
    "ItemNotFound",
    "NotEditableError",
    "StationHasNoTemplate",
    "FactCheckRunning",
    "StationBeingProduced",
    "StationNotFound",
    "StationNotEditable",
    "VersionNotFound",
]
