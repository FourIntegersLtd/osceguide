from __future__ import annotations

from app.core.errors import Conflict, Forbidden, NotFound
from app.core.tenancy import OrgNotFound

# Re-exported, not redefined: `require_org` in core raises this and the routers
# here document it, so both have to mean the same class.
__all__ = ["OrgNotFound"]


class OrgSlugTaken(Conflict):
    code = "org_slug_taken"
    default_message = "That slug is already in use"


class NotAMember(Forbidden):
    code = "not_a_member"
    default_message = "You are not a member of that organisation"


class MembershipExists(Conflict):
    code = "membership_exists"
    default_message = "That person already holds this role"


class MembershipNotFound(NotFound):
    code = "membership_not_found"
    default_message = "No such membership"


class PlatformAdminExists(Conflict):
    code = "platform_admin_exists"
    default_message = "That person already has staff console access"


class UserNotFound(NotFound):
    """No account for the address an administrator named.

    A membership is granted to a person who has registered; inviting somebody
    who has not is a different use case with its own flow.
    """

    code = "user_not_found"
    default_message = "No account for that email address"
