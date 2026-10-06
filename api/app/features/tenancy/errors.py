"""The errors an organisation, its memberships or the platform console can
refuse a request with.
"""

from __future__ import annotations

from app.core.errors import Conflict, Forbidden, InvalidInput, NotFound
from app.core.tenancy import OrgNotFound

# The same class identity raises. The console route documents it; there is not a second one.
from app.features.identity.errors import MfaNotEnrolled as MfaNotEnrolled

# Re-exported, not redefined: `require_org` in core raises this and the routers
# here document it, so both have to mean the same class.
__all__ = ["OrgNotFound"]


class OrgSlugTaken(Conflict):
    """Refuses to provision an organisation whose slug is already taken."""

    code = "org_slug_taken"
    default_message = "That slug is already in use"


class ContractDatesOutOfOrder(InvalidInput):
    """The contract would start after it ends."""

    code = "contract_dates_out_of_order"
    default_message = "The end date is before the start date"


class NotAMember(Forbidden):
    """Refuses to switch to a workspace this person does not belong to."""

    code = "not_a_member"
    default_message = "You are not a member of that organisation"


class MembershipExists(Conflict):
    """That person already holds this role at this organisation."""

    code = "membership_exists"
    default_message = "That person already holds this role"


class MembershipNotFound(NotFound):
    """No membership with that id exists at this organisation."""

    code = "membership_not_found"
    default_message = "No such membership"


class PlatformAdminExists(Conflict):
    """That person already has staff console access."""

    code = "platform_admin_exists"
    default_message = "That person already has staff console access"


class InvitationNotPending(Conflict):
    """That member has already chosen a password, or signs in through SSO."""

    code = "invitation_not_pending"
    default_message = "There is nothing to resend for that member"


class UserNotFound(NotFound):
    """No account for the address an administrator named.

    A membership is granted to a person who has registered; inviting somebody
    who has not is a different use case with its own flow.
    """

    code = "user_not_found"
    default_message = "No account for that email address"


class LastAdministrator(Conflict):
    """Revoking or demoting this member would leave the organisation without an administrator."""

    code = "last_admin"
    default_message = (
        "This is the organisation's last administrator. Make someone else an administrator first."
    )
