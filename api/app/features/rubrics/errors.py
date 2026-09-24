from __future__ import annotations

from app.core.errors import Conflict, InvalidInput, NotFound


class RubricNotFound(NotFound):
    code = "rubric_not_found"
    default_message = "No such rubric"


class RubricVersionNotFound(NotFound):
    code = "rubric_version_not_found"
    default_message = "No such rubric version"


class RubricVersionNotPublished(Conflict):
    code = "rubric_version_not_published"
    default_message = "That rubric version is not published"


class InvalidRubricError(InvalidInput):
    code = "invalid_rubric"
    default_message = "That rubric could not be marked against"


class NotEditableError(Conflict):
    code = "not_editable"
    default_message = "Only a draft can be edited"


class AlreadyPublishedError(Conflict):
    code = "already_published"
    default_message = "That version is already published"


class NotArchivableError(Conflict):
    code = "not_archivable"
    default_message = "Only a published version can be archived"


class VersionNotFound(NotFound):
    code = "version_not_found"
    default_message = "No such version"
