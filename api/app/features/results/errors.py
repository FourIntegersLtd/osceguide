from __future__ import annotations

from app.core.errors import Conflict, InvalidInput, NotFound

# Raised from here when a decision names something that is not a roster entry.
# Re-exported rather than restated so there is one `trainee_not_found`, and so
# the router can keep importing only its own errors.
from app.features.roster.errors import TraineeNotFound as TraineeNotFound


class ResultNotFound(NotFound):
    code = "result_not_found"
    default_message = "No decision has been recorded for that candidate"


class IncompatibleOutcomesError(InvalidInput):
    code = "incompatible_outcomes"
    default_message = "Those assessment and recruitment outcomes cannot go together"


class NotSignableError(InvalidInput):
    code = "not_signable"
    default_message = "This decision is not complete enough to sign off"


class InvalidWorkflowError(Conflict):
    code = "invalid_workflow"
    default_message = "That is not a step this decision can take"


class EvidenceChangedError(Conflict):
    """The station scores moved between sign-off and release.

    Without this a candidate receives an outcome nobody approved.
    """

    code = "evidence_changed"
    default_message = "The evidence has changed since sign-off; review and sign off again"


class NotReleased(NotFound):
    code = "result_not_released"
    default_message = "Your result has not been released yet"
