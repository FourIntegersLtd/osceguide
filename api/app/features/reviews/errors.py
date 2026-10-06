"""The refusals a reviews route can return. Clients branch on each one's `code`."""

from __future__ import annotations

from app.core.errors import Conflict, InvalidInput, NotFound


class InvalidRatingError(InvalidInput):
    """A rating was not one the sitting's rubric allows, or a GP lead's verdict was not G, A or R."""

    code = "invalid_rating"
    default_message = "That is not a rating this rubric allows"


class InvalidStatusError(InvalidInput):
    """A review's status was neither draft nor completed."""

    code = "invalid_review_status"
    default_message = "A review is either a draft or completed"


class ReviewIncompleteError(Conflict):
    """A review was marked completed without scoring every required domain."""

    code = "review_incomplete"
    default_message = "Score every domain before completing the review"


class NothingToReviewError(Conflict):
    """The station has no reviewable feedback domains, so there is nothing to complete."""

    code = "nothing_to_review"
    default_message = "This station has no reviewable feedback domains yet"


class ReviewConflictError(Conflict):
    """Someone else saved first. 409 rather than a silent overwrite."""

    code = "review_conflict"
    default_message = "Someone else has changed this review since you opened it"


class SlotNotFound(NotFound):
    """No such slot in this organisation.

    Deliberately indistinguishable from a slot that does not exist at all: a
    different answer would confirm to one tenant that another's slot id is
    real.
    """

    code = "slot_not_found"
    default_message = "No such slot"
