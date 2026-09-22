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


class StationNotFound(NotFound):
    """Mirrors `stations.errors.StationNotFound`, and shares its code (S3).

    A comment names a station. Naming one that does not exist used to reach
    the insert and answer `internal_error` — the foreign key doing the
    refusal, unmapped. Declared here for the reason `UnknownExamError` is:
    this slice's routes document their own errors.
    """

    code = "station_not_found"
    default_message = "No such station"
