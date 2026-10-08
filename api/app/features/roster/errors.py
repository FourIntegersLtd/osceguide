"""The errors a roster action can refuse with: an unknown trainee, cohort or
group, a duplicate, or a person a circuit may not examine.
"""

from __future__ import annotations

from typing import Any

from app.core.errors import AppError, Conflict, InvalidInput, NotFound

# Re-exported so the add route documents the refusal a weak temporary password gets.
from app.features.identity.errors import WeakPasswordError as WeakPasswordError


class TraineeNotFound(NotFound):
    """No trainee with that id is on this organisation's roster."""

    code = "trainee_not_found"
    default_message = "No such trainee"


class TraineeExists(Conflict):
    """Someone with that email is already rostered at this organisation."""

    code = "trainee_exists"
    default_message = "Someone with that email is already on this roster"


class TooManyTrainees(InvalidInput):
    """One bulk import carried more rows than one request takes."""

    code = "too_many_trainees"
    default_message = "An import takes at most 500 trainees at a time"


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


# --- SCIM (E-21) ------------------------------------------------------------------

SCIM_ERROR_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:Error"


class ScimError(AppError):
    """A refusal on the SCIM routes, in the body an identity provider reads (RFC 7644 §3.12).

    `code` rides along beside the SCIM fields: a connector ignores it, and it
    is what the rest of this API's error contract is checked against.
    """

    status = 400
    code = "scim_invalid_value"
    default_message = "The request was not valid SCIM"
    media_type = "application/scim+json"
    # RFC 7644's `scimType`, where the RFC names one for this refusal.
    scim_type: str | None = "invalidValue"

    def envelope(self) -> dict[str, Any] | None:
        """The SCIM error body."""
        body: dict[str, Any] = {
            "schemas": [SCIM_ERROR_SCHEMA],
            "status": str(self.status),
            "detail": self.message,
            "code": self.code,
        }
        if self.scim_type is not None:
            body["scimType"] = self.scim_type
        return body


class ScimUnauthorized(ScimError):
    """No bearer token, or one this organisation did not issue or has revoked."""

    status = 401
    code = "scim_unauthorized"
    default_message = "A valid SCIM bearer token for this organisation is required"
    scim_type = None


class ScimResourceNotFound(ScimError):
    """No user or group by that id on this organisation's roster."""

    status = 404
    code = "scim_not_found"
    default_message = "No such resource"
    scim_type = None


class ScimUniqueness(ScimError):
    """A user with that userName, or a group with that displayName, already exists."""

    status = 409
    code = "scim_uniqueness"
    default_message = "That resource already exists"
    scim_type = "uniqueness"


class ScimInvalidFilter(ScimError):
    """A filter this server does not understand. Only `attribute eq "value"` is supported."""

    status = 400
    code = "scim_invalid_filter"
    default_message = 'Only a single `attribute eq "value"` filter is supported'
    scim_type = "invalidFilter"


class ScimMutability(ScimError):
    """An attempt to change what the roster does not let change: a user's email address."""

    status = 400
    code = "scim_mutability"
    default_message = "userName cannot be changed; it is the address the account was linked by"
    scim_type = "mutability"


class ScimTokenNotFound(NotFound):
    """No SCIM token by that id belongs to this organisation."""

    code = "scim_token_not_found"
    default_message = "No such SCIM token"
