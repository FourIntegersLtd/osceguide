"""The refusals a results route can return. Clients branch on each one's `code`."""

from __future__ import annotations

from app.core.errors import Conflict, Forbidden, InvalidInput, NotFound

# Raised from here when a decision names something that is not a roster entry.
# Re-exported rather than restated so there is one `trainee_not_found`, and so
# the router can keep importing only its own errors.
from app.features.roster.errors import TraineeNotFound as TraineeNotFound
from app.features.sittings.errors import SittingNotFound as SittingNotFound


class ResultNotFound(NotFound):
    """No decision has been recorded yet for this candidate on this sitting."""

    code = "result_not_found"
    default_message = "No decision has been recorded for that candidate"


class IncompatibleOutcomesError(InvalidInput):
    """The assessment and recruitment outcome given cannot both be true."""

    code = "incompatible_outcomes"
    default_message = "Those assessment and recruitment outcomes cannot go together"


class RecruitmentOutsideExamError(InvalidInput):
    """A recruitment outcome was given for a training sitting; only exam mode records one."""

    code = "recruitment_outside_exam"
    default_message = "A recruitment outcome is recorded only for an exam-mode sitting"


class DecisionOutsideExamError(Conflict):
    """A decision was asked for on a training sitting, which stops at marking."""

    code = "decision_outside_exam"
    default_message = "Decisions are recorded for exam-mode sittings only"


class CandidateDidNotSitError(Conflict):
    """A decision was asked for somebody who sat no station on this sitting."""

    code = "candidate_did_not_sit"
    default_message = "This candidate did not sit any station on this sitting"


class HireReasonRequiredError(InvalidInput):
    """An employer recorded "hired" with no reason."""

    code = "hire_reason_required"
    default_message = "Give a reason before recording a hire"


class NotSignableError(InvalidInput):
    """The decision is missing an outcome or a rationale, so it cannot be signed off."""

    code = "not_signable"
    default_message = "This decision is not complete enough to sign off"


class InvalidWorkflowError(Conflict):
    """The requested step is not reachable from where this decision is now."""

    code = "invalid_workflow"
    default_message = "That is not a step this decision can take"


class EvidenceChangedError(Conflict):
    """The station scores moved between sign-off and release.

    Without this a candidate receives an outcome nobody approved.
    """

    code = "evidence_changed"
    default_message = "The evidence has changed since sign-off; review and sign off again"


class NotReleasableError(Conflict):
    """The outcome is withheld or inconclusive, so it is not sent to the candidate."""

    code = "outcome_not_releasable"
    default_message = "A withheld or inconclusive outcome cannot be released"


class DecisionRevisedError(Conflict):
    """The decision was saved by someone else since the caller read it.

    Its own code rather than the bare `conflict`, because the client's response
    is "reload and re-check", not "your request was wrong".
    """

    code = "decision_revised"
    default_message = "This decision has changed since you loaded it"


class NotReleased(NotFound):
    """The candidate asked for a result that has not been sent to them yet."""

    code = "result_not_released"
    default_message = "Your result has not been released yet"


class ReviewsPendingError(Conflict):
    """A review of one of the candidate's stations is still a draft, so the decision is not signed (R-33)."""

    code = "reviews_pending"
    default_message = "A review of this candidate is still in progress; complete it before signing off"


class AppealNotFound(NotFound):
    """No appeal by that id in this organisation."""

    code = "appeal_not_found"
    default_message = "That appeal was not found"


class AppealAlreadyOpen(Conflict):
    """A review of this result has already been asked for and is not finished."""

    code = "appeal_already_open"
    default_message = "A review of this result has already been requested"


class AppealClosed(Conflict):
    """The appeal is resolved or declined, so it takes no more steps."""

    code = "appeal_closed"
    default_message = "This appeal has already been decided"


class AppealNotAssigned(Conflict):
    """The outcome was recorded before a second marker was assigned."""

    code = "appeal_not_assigned"
    default_message = "Assign a second marker before recording the outcome"


class AppealStale(Conflict):
    """The result moved since the appeal was made, so the outcome would supersede the wrong revision."""

    code = "appeal_stale"
    default_message = "The result has changed since this appeal was made"


class NotAssignedMarker(Forbidden):
    """Someone other than the assigned second marker tried to record the outcome."""

    code = "not_assigned_marker"
    default_message = "Only the assigned second marker can record the outcome"


class SecondMarkerMustDiffer(InvalidInput):
    """The person who signed off or released the result cannot be its second marker."""

    code = "second_marker_must_differ"
    default_message = "A second marker must be someone who did not sign off or release the result"


class AssigneeNotAdmin(InvalidInput):
    """The person named cannot record a result outcome in this organisation."""

    code = "assignee_not_admin"
    default_message = "A second marker must be an administrator of this organisation"


class ConfirmationMismatch(InvalidInput):
    """The typed confirmation does not match the candidate, so nothing was deleted."""

    code = "confirmation_mismatch"
    default_message = "The confirmation does not match this candidate's address"


class AppealOpenForCandidate(Conflict):
    """The candidate's data is held while a review of their result is open."""

    code = "appeal_open"
    default_message = "Decide the open review of this candidate's result before deleting their data"


class DecisionsIncompleteError(Conflict):
    """The sheet cannot be signed off while any candidate has no decision."""

    code = "decisions_incomplete"
    default_message = "Every candidate needs a decision before the results can be signed off"
