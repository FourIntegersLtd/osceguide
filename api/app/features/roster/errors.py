"""The errors a roster action can refuse with: an unknown trainee, cohort or
group, a duplicate, or a person a circuit may not examine.
"""

from __future__ import annotations

from app.core.errors import Conflict, NotFound


class TraineeNotFound(NotFound):
    """No trainee with that id is on this organisation's roster."""

    code = "trainee_not_found"
    default_message = "No such trainee"


class TraineeExists(Conflict):
    """Someone with that email is already rostered at this organisation."""

    code = "trainee_exists"
    default_message = "Someone with that email is already on this roster"


class CohortNotFound(NotFound):
    """No cohort with that id exists at this organisation."""

    code = "cohort_not_found"
    default_message = "No such cohort"


class CohortExists(Conflict):
    """A cohort with that name already exists at this organisation."""

    code = "cohort_exists"
    default_message = "A cohort with that name already exists"


class CohortInUse(Conflict):
    """Refuses to delete a cohort that still has trainees in it."""

    code = "cohort_in_use"
    default_message = "That cohort still has trainees in it"


class GroupNotFound(NotFound):
    """No group with that id exists at this organisation."""

    code = "group_not_found"
    default_message = "No such group"


class GroupExists(Conflict):
    """A group with that label already exists at this organisation."""

    code = "group_exists"
    default_message = "A group with that label already exists"


class GroupNotEmpty(Conflict):
    """Refuses to delete a group that still has members."""

    code = "group_not_empty"
    default_message = "That group still has members"


class TraineeRevokedError(Conflict):
    """Refuses an action because the trainee's access has been revoked."""

    code = "trainee_revoked"
    default_message = "That trainee's access has been revoked"


class TraineeNotOnRosterError(Conflict):
    """SEC-014: a circuit may only examine people this organisation has
    rostered. A `users.id` with no linked trainee row here is refused rather
    than silently enrolled."""

    code = "trainee_not_on_roster"
    default_message = "That person is not on this organisation's roster, so they cannot be examined here."


class InvitationNotPending(Conflict):
    """Refuses to re-send an invitation to someone who already chose a password."""

    code = "invitation_not_pending"
    default_message = "That person has already chosen a password, so there is no invitation to re-send"


class TraineeInUse(Conflict):
    """Raised on the `candidate_result_revisions.trainee_id RESTRICT` violation.
    Revoking access is the mechanism everywhere else; this is only for a row
    nobody ever examined.
    """

    code = "trainee_in_use"
    default_message = "This trainee has a decision recorded and cannot be deleted. Revoke access instead."
