from __future__ import annotations

from app.core.errors import Conflict, Forbidden, NotFound


class OrgNotFound(NotFound):
    code = "org_not_found"
    default_message = "No such organisation"


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
