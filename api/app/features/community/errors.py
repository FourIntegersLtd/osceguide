from __future__ import annotations

from app.core.errors import Forbidden, InvalidInput, NotFound


class PostNotFound(NotFound):
    code = "post_not_found"
    default_message = "No such post"


class NotYoursError(Forbidden):
    code = "post_not_yours"
    default_message = "You can only remove your own posts"


class EmptyContentError(InvalidInput):
    code = "empty_content"
    default_message = "There is nothing to post"


class ContentTooLongError(InvalidInput):
    code = "content_too_long"
    default_message = "That post is too long"
