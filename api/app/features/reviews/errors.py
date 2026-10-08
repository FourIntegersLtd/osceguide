"""The refusals a reviews route can return. Clients branch on each one's `code`."""

from __future__ import annotations

from app.core.errors import Conflict, Forbidden, InvalidInput, NotFound

# Re-exported rather than restated, so there is one `circuit_not_found` and one
# `trainee_not_found`, and the router imports only its own errors.
from app.features.attempts.errors import AttemptNotFound as AttemptNotFound
from app.features.attempts.errors import InvalidAttemptState as InvalidAttemptState
from app.features.roster.errors import TraineeNotFound as TraineeNotFound
from app.features.sittings.errors import CircuitNotFound as CircuitNotFound


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


class ReviewLockedError(Conflict):
    """The candidate's decision has been signed off or released, so the reviews behind it are fixed."""

    code = "review_locked"
    default_message = (
        "This candidate's result has been signed off or released, so its reviews can no longer be changed"
    )


class ReviewNotFound(NotFound):
    """No such review on this slot."""

    code = "review_not_found"
    default_message = "No such review"


class ReviewNotDraftError(Conflict):
    """Only a draft is withdrawn; a completed review is part of the record and is edited instead."""

    code = "review_not_draft"
    default_message = "Only a draft review can be withdrawn"


class SlotNotFound(NotFound):
    """No such slot in this organisation.

    Deliberately indistinguishable from a slot that does not exist at all: a
    different answer would confirm to one tenant that another's slot id is
    real.
    """

    code = "slot_not_found"
    default_message = "No such slot"


class NotReviewerError(Forbidden):
    """Only an institution administrator, or the supervisor named on the slot's circuit, reviews it (R-9)."""

    code = "not_slot_reviewer"
    default_message = "Only the supervisor named on this circuit, or an administrator, can review it"


class CircuitReviewFinalizedError(Conflict):
    """The circuit's review has already been finalised; it is not finalised twice (R-10)."""

    code = "circuit_review_finalized"
    default_message = "This circuit's review has already been finalised"
