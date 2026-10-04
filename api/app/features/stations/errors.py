"""The errors this slice's routes can raise: stations, station templates, photos and generation
profiles. Each carries the `code` a client branches on.
"""

from __future__ import annotations

from app.core.errors import Conflict, InvalidInput, NotFound, Unavailable


class StationNotFound(NotFound):
    """No such station in this organisation, or the library."""

    code = "station_not_found"
    default_message = "No such station"


class VersionNotFound(NotFound):
    """No such station version, on a station that does exist."""

    code = "version_not_found"
    default_message = "No such version"


class StationFlagNotFound(NotFound):
    """No such reported problem against a station."""

    code = "station_flag_not_found"
    default_message = "No such report on a station"


class NotEditableError(Conflict):
    """A published version was asked to change in place; a new draft version is what changes."""

    code = "not_editable"
    default_message = "Published content cannot be edited; create a new version"


class FactCheckRunning(Conflict):
    """A fact check of this version is already running; its result is on its way."""

    code = "fact_check_running"
    default_message = "This version's facts are already being checked"


class NotDeletableError(Conflict):
    """Only a draft can be deleted; a published or archived version is a record of what ran."""

    code = "not_deletable"
    default_message = "Only a draft can be deleted"


class AlreadyPublishedError(Conflict):
    """Publishing a version that is already published."""

    code = "already_published"
    default_message = "That version is already published"


class NotArchivableError(Conflict):
    """Only a published version can be archived; a draft is deleted instead."""

    code = "not_archivable"
    default_message = "Only a published version can be archived"


class StationNotPublishedError(Conflict):
    """A circuit or an attempt named a station that is still a draft (T4).

    Its own code rather than `not_editable`: the client's message is "publish
    this station before scheduling it", which is a different instruction.
    """

    code = "station_not_published"
    default_message = "A circuit can only use a published station"


class TemplateNotPublishedError(Conflict):
    """A station was built on a template version that is still a draft."""

    code = "template_not_published"
    default_message = "A station can only be built on a published template version"


class UnknownExamError(NotFound):
    """A station named an exam that is not published.

    Mirrors `catalog.errors.UnknownExamError` rather than importing it: a
    router may only reach into its own slice, and each slice owning its
    exception type is what keeps that true. The *code* is deliberately shared —
    it is the API contract, and the client sees one vocabulary — so a unit test
    pins the two together.
    """

    code = "unknown_exam"
    default_message = "No such exam"


class StationTemplateNotFound(NotFound):
    """No such station template in this organisation.

    A different thing from a *feedback* template: this is the shape a station
    takes, that one is the rubric it is marked with. Separate codes because the
    client's answer differs — one sends the author back to the template list,
    the other to the rubric list.
    """

    code = "station_template_not_found"
    default_message = "No such station template"


class StationTemplateVersionNotFound(NotFound):
    """No such version of a station template that does exist."""

    code = "station_template_version_not_found"
    default_message = "No such station template version"


class GenerationProfileNotFound(NotFound):
    """No such autogeneration profile key."""

    code = "generation_profile_not_found"
    default_message = "No such generation profile"


# Re-exported, not redefined: browsing another exam's library is refused with
# the same code starting an attempt in it is, and two classes with one code
# would drift.
from app.features.entitlements.errors import NotEntitled  # noqa: E402
from app.features.generation.errors import GenerationUnavailable  # noqa: E402

__all__ = ["NotEntitled", "GenerationUnavailable"]


class InvalidPhotoError(InvalidInput):
    """An upload that failed `domain_photos.validate_upload` or `ensure_real_image`."""

    code = "invalid_photo"
    default_message = "That file cannot be used as a station image"


class NotAMediaBlockError(InvalidInput):
    """An upload naming a block that is not a `media` block on the station's template.

    An unbound station has no template, so it has no media blocks either.
    """

    code = "not_a_media_block"
    default_message = "That block does not take images"


class PhotoNotOnStationError(NotFound):
    """Deleting an image that is not on this station.

    The retiring route deleted whatever key it was handed, so any authorised
    caller could destroy any object in the bucket by naming its URL.
    """

    code = "photo_not_on_station"
    default_message = "That image is not on this station"


class InvalidImportFileError(InvalidInput):
    """An upload that cannot be imported as a station: wrong type, wrong size, or nothing to read."""

    code = "invalid_import_file"
    default_message = "That file cannot be imported as a station"


class StationImportNotFound(NotFound):
    """No such station import for this owner."""

    code = "station_import_not_found"
    default_message = "No such station import"


class ImportNotReadyError(Conflict):
    """A station was asked for from an import that has no template yet, or is already being drafted."""

    code = "import_not_ready"
    default_message = "That import is not ready for a station to be drafted"


class PhotoStorageUnavailable(Unavailable):
    """No object storage is configured, so a photo upload or delete cannot proceed."""

    code = "photo_storage_unavailable"
    default_message = "Image storage is not configured"
