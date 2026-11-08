"""The errors this slice's routes can raise: stations, station templates, photos and generation
profiles. Each carries the `code` a client branches on.
"""

from __future__ import annotations

from app.core.errors import Conflict, Forbidden, InvalidInput, NotFound, Unavailable


class StationNotFound(NotFound):
    """No such station in this organisation, or the library."""

    code = "station_not_found"
    default_message = "We couldn't find that station"


class StationNotInPlan(Forbidden):
    """A platform library station outside the window this person's paid plan unlocks.

    Hidden from the library rather than locked: this is raised only when something tries to
    read or start the station directly, by a known id, past the list that already left it out.
    """

    code = "station_not_in_plan"
    default_message = "This station is not included in your plan. Upgrade to unlock it."


class VersionNotFound(NotFound):
    """No such station version, on a station that does exist."""

    code = "version_not_found"
    default_message = "We couldn't find that version"


class StationFlagNotFound(NotFound):
    """No such reported problem against a station."""

    code = "station_flag_not_found"
    default_message = "We couldn't find that report on a station"


class NotEditableError(Conflict):
    """A published version was asked to change in place; a new draft version is what changes."""

    code = "not_editable"
    default_message = "Published content can't be edited. Create a new version to make changes."


class StationEmptyError(Conflict):
    """A draft with nothing written in it was asked to go live."""

    code = "station_empty"
    default_message = "This station has no content yet. Write it before publishing."


class StationNotApprovableError(Conflict):
    """A station was asked to be approved while it is not `published` — a draft or archived
    station has no reader to protect yet, so the editor's sign-off has nothing to act on."""

    code = "station_not_approvable"
    default_message = "Only a published station can be approved"


class FactCheckRunning(Conflict):
    """A fact check of this version is already running; its result is on its way."""

    code = "fact_check_running"
    default_message = "This version's facts are already being checked"


class StationBeingProduced(Conflict):
    """The agent is working on this version; a save now would be overwritten by its next step."""

    code = "station_being_produced"
    default_message = (
        "The AI assistant is still working on this version. Wait for it to finish, or stop it first."
    )


class NotDeletableError(Conflict):
    """Only a draft can be deleted; a published or archived version is a record of what ran."""

    code = "not_deletable"
    default_message = "Only a draft can be deleted"


class DraftExistsError(Conflict):
    """The station already has an open draft; a second would leave one's edits behind."""

    code = "draft_exists"
    default_message = "The station already has a draft. Publish or delete it first"


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
    default_message = "Only published stations can be added to a circuit."


class TemplateNotPublishedError(Conflict):
    """A station was built on a template version that is still a draft."""

    code = "template_not_published"
    default_message = "A station can only be built from a published template. Publish the template first."


class UnknownExamError(NotFound):
    """A station named an exam that is not published.

    Mirrors `catalog.errors.UnknownExamError` rather than importing it: a
    router may only reach into its own slice, and each slice owning its
    exception type is what keeps that true. The *code* is deliberately shared —
    it is the API contract, and the client sees one vocabulary — so a unit test
    pins the two together.
    """

    code = "unknown_exam"
    default_message = "We couldn't find that exam"


class StationTemplateNotFound(NotFound):
    """No such station template in this organisation.

    A different thing from a *feedback* template: this is the shape a station
    takes, that one is the rubric it is marked with. Separate codes because the
    client's answer differs — one sends the author back to the template list,
    the other to the rubric list.
    """

    code = "station_template_not_found"
    default_message = "We couldn't find that station template"


class StationTemplateVersionNotFound(NotFound):
    """No such version of a station template that does exist."""

    code = "station_template_version_not_found"
    default_message = "We couldn't find that station template version"


class GenerationProfileNotFound(NotFound):
    """No such autogeneration profile key."""

    code = "generation_profile_not_found"
    default_message = "We couldn't find that generation profile"


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
    default_message = "You can't add an image to that part of the station."


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
    default_message = "We couldn't find that station import"


class ImportNotReadyError(Conflict):
    """A station was asked for from an import that has no template yet, or is already being drafted."""

    code = "import_not_ready"
    default_message = "That import isn't finished yet, so a station can't be drafted from it."


class PhotoStorageUnavailable(Unavailable):
    """No object storage is configured, so a photo upload or delete cannot proceed."""

    code = "photo_storage_unavailable"
    default_message = "Image uploads aren't available right now. Please try again later."
