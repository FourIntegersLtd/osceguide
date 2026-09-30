"""The refusals a rubrics route can return. Clients branch on each one's `code`."""

from __future__ import annotations

from app.core.errors import Conflict, InvalidInput, NotFound


class RubricNotFound(NotFound):
    """No rubric matches the id, or it belongs to a different owner."""

    code = "rubric_not_found"
    default_message = "No such rubric"


class RubricVersionNotFound(NotFound):
    """No version with that number exists on this rubric."""

    code = "rubric_version_not_found"
    default_message = "No such rubric version"


class RubricVersionNotPublished(Conflict):
    """Something tried to mark against a version that is still a draft."""

    code = "rubric_version_not_published"
    default_message = "That rubric version is not published"


class InvalidRubricError(InvalidInput):
    """The structure or pacing given could not be parsed or would not run."""

    code = "invalid_rubric"
    default_message = "That rubric could not be marked against"


class NotEditableError(Conflict):
    """The version has already been published, so its body is now fixed."""

    code = "not_editable"
    default_message = "Only a draft can be edited"


class AlreadyPublishedError(Conflict):
    """Publish was called on a version that is already published."""

    code = "already_published"
    default_message = "That version is already published"


class NotArchivableError(Conflict):
    """Only a published version can be retired from use; a draft has nothing to archive."""

    code = "not_archivable"
    default_message = "Only a published version can be archived"
