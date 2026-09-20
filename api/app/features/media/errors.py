from __future__ import annotations

from app.core.errors import Conflict, InvalidInput, NotFound


class ItemNotFound(NotFound):
    code = "media_not_found"
    default_message = "No such item"


class UnknownMediaKindError(InvalidInput):
    code = "unknown_media_kind"
    default_message = "That is not a kind of study material"


class NotEditableError(Conflict):
    code = "media_not_editable"
    default_message = "Published material is replaced, not edited in place"


class AlreadyPublishedError(Conflict):
    code = "media_already_published"
    default_message = "That is already published"


class UnusableTitleError(InvalidInput):
    code = "unusable_title"
    default_message = "That title has nothing a URL can be made from"


class EmptyQueryError(InvalidInput):
    code = "empty_query"
    default_message = "Type something to search for"


class InvalidListStatusError(InvalidInput):
    code = "invalid_media_status"
    default_message = "Status must be draft, published, or all"


class NotDeletableError(Conflict):
    code = "media_not_deletable"
    default_message = "Only drafts can be deleted"


class SlugTaken(Conflict):
    code = "slug_taken"
    default_message = "Something with that title already exists"


class UnknownExamError(NotFound):
    """Mirrors `catalog.errors.UnknownExamError`, and shares its code.

    Declared here so this slice's routes can document the refusal without
    importing another slice's error class into their signatures — the same
    reason `stations` and `attempts` mirror it. It became reachable in
    practice once exams stopped being four seeded rows: a code that names no
    published exam is now an ordinary thing for a client to send.
    """

    code = "unknown_exam"
    default_message = "No such exam"
