"""Who may do what, and in which organisation.

Pure rules: no database, no HTTP, no session. Every predicate here is ported
from the legacy b2b policy, which is the current production behaviour and is
correct — `tests/unit/test_tenancy_domain.py` carries its assertions as the
oracle. The rules live here rather than in route handlers so they can be read
in one place and tested without a container.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

# Roles that may administer an organisation. `platform_admin` is deliberately
# absent: a console admin manages organisations from the outside and inherits
# none of their powers, so revoking someone's org membership genuinely removes
# their access even if they also run the platform.
ORG_ADMIN_ROLES = frozenset({"owner", "admin", "institution_admin", "partner_admin"})

# The narrower set that may sign off and release a candidate's result. A
# partner admin runs a practice surface and never an examination, so it is an
# org admin without being an institution admin.
INSTITUTION_ADMIN_ROLES = frozenset({"owner", "admin", "institution_admin"})

# End users: people who sit stations rather than run them.
END_USER_ROLES = frozenset({"trainee", "practice_user"})

ASSIGNED_STAFF_ROLE = "supervisor"

# Organisation statuses that permit signing in. A suspended or churned tenant
# keeps its data and loses its access.
ACTIVE_ORG_STATUSES = frozenset({"trial", "active"})


def normalize_role(role: str | None) -> str:
    return str(role or "").strip().lower()


def is_org_admin(role: str | None) -> bool:
    return normalize_role(role) in ORG_ADMIN_ROLES


def is_institution_admin(role: str | None) -> bool:
    return normalize_role(role) in INSTITUTION_ADMIN_ROLES


def is_assigned_staff(role: str | None) -> bool:
    return normalize_role(role) == ASSIGNED_STAFF_ROLE


def is_trainee(role: str | None) -> bool:
    return normalize_role(role) in END_USER_ROLES


def may_read_org(role: str | None) -> bool:
    """Any member role may read org context; writing is gated per resource."""
    return is_org_admin(role) or is_assigned_staff(role) or is_trainee(role)


def org_permits_access(status: str | None) -> bool:
    return str(status or "").strip().lower() in ACTIVE_ORG_STATUSES


@dataclass(frozen=True)
class MembershipRef:
    """A membership as the token carries it: enough to authorise, nothing more."""

    org_slug: str
    role: str
    org_type: str | None = None
    surface: str | None = None

    @property
    def slug(self) -> str:
        return self.org_slug.strip()


def pick_default_workspace(
    memberships: Sequence[MembershipRef], preferred_order: Iterable[str]
) -> MembershipRef | None:
    """The workspace a user lands in when they sign in.

    Preference order wins, so a user who belongs to several organisations keeps
    landing where they last worked. A preference naming nothing they belong to
    falls back to their first real membership rather than leaving them with no
    workspace at all — which would make every org-scoped route 403 for someone
    who is plainly a member.
    """
    valid = [m for m in memberships if m.slug]
    if not valid:
        return None
    for raw in preferred_order:
        slug = str(raw or "").strip()
        if not slug:
            continue
        match = next((m for m in valid if m.slug == slug), None)
        if match:
            return match
    return valid[0]


def resolve_workspace(memberships: Sequence[MembershipRef], org_slug: str) -> MembershipRef | None:
    """The membership a switch-workspace request names, or None to refuse it.

    None means 403. Returning the unchanged workspace instead would let a user
    believe they had switched into an organisation they cannot see.
    """
    slug = str(org_slug or "").strip()
    if not slug:
        return None
    return next((m for m in memberships if m.slug == slug), None)
