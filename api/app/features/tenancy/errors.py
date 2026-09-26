"""The errors an organisation, its memberships or the platform console can
refuse a request with.
"""

from __future__ import annotations

from app.core.errors import Conflict, Forbidden, NotFound
from app.core.tenancy import OrgNotFound

# Re-exported, not redefined: `require_org` in core raises this and the routers
# here document it, so both have to mean the same class.
__all__ = ["OrgNotFound"]


class OrgSlugTaken(Conflict):
    """Refuses to provision an organisation whose slug is already taken."""

    code = "org_slug_taken"
    default_message = "That slug is already in use"


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


class UserNotFound(NotFound):
    """No account for the address an administrator named.

    A membership is granted to a person who has registered; inviting somebody
    who has not is a different use case with its own flow.
    """

    code = "user_not_found"
    default_message = "No account for that email address"
