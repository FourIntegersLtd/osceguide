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


class SlugTaken(Conflict):
    code = "slug_taken"
    default_message = "Something with that title already exists"
