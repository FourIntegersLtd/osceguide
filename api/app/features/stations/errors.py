from __future__ import annotations

from app.core.errors import Conflict, NotFound


class StationNotFound(NotFound):
    code = "station_not_found"
    default_message = "No such station"


class VersionNotFound(NotFound):
    code = "version_not_found"
    default_message = "No such version"


class NotEditableError(Conflict):
    code = "not_editable"
    default_message = "Published content cannot be edited; create a new version"


class NotDeletableError(Conflict):
    code = "not_deletable"
    default_message = "Only a draft can be deleted"


class AlreadyPublishedError(Conflict):
    code = "already_published"
    default_message = "That version is already published"


class NotArchivableError(Conflict):
    code = "not_archivable"
    default_message = "Only a published version can be archived"


class TemplateNotPublishedError(Conflict):
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


class TemplateVersionNotFound(NotFound):
    """No such feedback template version in this organisation.

    Indistinguishable from one that does not exist, so a template id cannot be
    probed across tenants.
    """

    code = "feedback_template_version_not_found"
    default_message = "No such feedback template version"
