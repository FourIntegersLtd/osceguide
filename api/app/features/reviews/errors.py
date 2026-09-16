from __future__ import annotations

from app.core.errors import Conflict, InvalidInput, NotFound


class ReviewNotFound(NotFound):
    code = "review_not_found"
    default_message = "No such review"


class InvalidRagError(InvalidInput):
    code = "invalid_rag"
    default_message = "A rating must be R, A or G"


class InvalidStatusError(InvalidInput):
    code = "invalid_review_status"
    default_message = "A review is either a draft or completed"


class ReviewIncompleteError(Conflict):
    code = "review_incomplete"
    default_message = "Score every domain before completing the review"


class NothingToReviewError(Conflict):
    code = "nothing_to_review"
    default_message = "This station has no reviewable feedback domains yet"


class ReviewConflictError(Conflict):
    """Someone else saved first.

    409 rather than a silent overwrite: b2b's client detects this by matching
    the words "another user" in an error string.
    """

    code = "review_conflict"
    default_message = "Someone else has changed this review since you opened it"
