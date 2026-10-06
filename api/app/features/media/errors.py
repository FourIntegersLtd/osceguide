"""The refusals a media route can return. Clients branch on each one's `code`."""

from __future__ import annotations

from app.core.errors import Conflict, InvalidInput, NotFound


class ItemNotFound(NotFound):
    """Raised when a media item id or slug does not match anything stored."""

    code = "media_not_found"
    default_message = "No such item"


class UnknownMediaKindError(InvalidInput):
    """Raised when a request names a media kind that is not slide_deck, summary, blog or podcast."""

    code = "unknown_media_kind"
    default_message = "That is not a kind of study material"


class BeingProduced(Conflict):
    """Raised when a draft is saved while a production job is working on it: one would overwrite the other."""

    code = "media_being_produced"
    default_message = "Production is in progress for this item; wait for it to finish or stop it"


class NotEditableError(Conflict):
    """Raised when someone tries to change a published item's content in place, rather than replacing it."""

    code = "media_not_editable"
    default_message = "A published item's content is replaced, not edited in place"


class AlreadyPublishedError(Conflict):
    """Raised when someone tries to publish an item that is already published."""

    code = "media_already_published"
    default_message = "That is already published"


class UnusableTitleError(InvalidInput):
    """Raised when a title has no characters a URL slug can be built from."""

    code = "unusable_title"
    default_message = "That title has nothing a URL can be made from"


class EmptyQueryError(InvalidInput):
    """Raised when a search request carries no search text."""

    code = "empty_query"
    default_message = "Type something to search for"


class InvalidListStatusError(InvalidInput):
    """Raised when a list request's status filter is not draft, published, or all."""

    code = "invalid_media_status"
    default_message = "Status must be draft, published, or all"


class NotDeletableError(Conflict):
    """Raised when someone tries to delete an item that has already been published."""

    code = "media_not_deletable"
    default_message = "Only drafts can be deleted"


class SlugTaken(Conflict):
    """Raised when another item already has the URL slug a new or renamed item would need."""

    code = "slug_taken"
    default_message = "Something with that title already exists"


class UnknownExamError(NotFound):
    """Mirrors `catalog.errors.UnknownExamError`, and shares its code.

    Declared here so this slice's routes can document the refusal without
    importing another slice's error class into their signatures.
    """

    code = "unknown_exam"
    default_message = "No such exam"
