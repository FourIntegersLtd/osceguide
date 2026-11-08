"""Who may do what, and in which organisation.

Pure rules: no database, no HTTP, no session. `tests/unit/test_tenancy_domain.py` carries
the assertions as the oracle.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

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
TRAINEE_ROLE = "trainee"
END_USER_ROLES = frozenset({TRAINEE_ROLE, "practice_user"})

ASSIGNED_STAFF_ROLE = "supervisor"

# Hire's lead assessor: an assessor (`supervisor`) who also writes the lead review that settles a
# station's marks. The screen says "Lead assessor" on hire and "GP lead" on an institution; only an
# employer organisation may seat one (`EMPLOYER_ONLY_ROLES`), so an institution's roles are unchanged.
LEAD_ASSESSOR_ROLE = "gp_lead"
ASSIGNED_STAFF_ROLES = frozenset({ASSIGNED_STAFF_ROLE, LEAD_ASSESSOR_ROLE})
EMPLOYER_ONLY_ROLES = frozenset({LEAD_ASSESSOR_ROLE})

# Every role that may legitimately be written to a membership row. A role
# outside this set is not a permission the product has — it is a typo or an
# attempt to invent one — and is refused rather than stored. `platform_admin`
# is deliberately absent: it is a property of the user, never an org role.
GRANTABLE_ROLES = ORG_ADMIN_ROLES | END_USER_ROLES | ASSIGNED_STAFF_ROLES

# How far a role reaches, so a grant can be checked against the granter's own
# standing. An org admin may seat people at or below their own tier and no
# higher: without this a `partner_admin` (which must never run an examination)
# could hand itself `institution_admin` and sign off results. `owner` sits
# above the examination tier so that granting `owner`/`institution_admin` is
# reserved to those who already hold it.
_ROLE_RANK: dict[str, int] = {
    "owner": 4,
    "admin": 3,
    "institution_admin": 3,
    "partner_admin": 2,
    ASSIGNED_STAFF_ROLE: 1,
    LEAD_ASSESSOR_ROLE: 1,
    "trainee": 0,
    "practice_user": 0,
}

# Organisation statuses that permit signing in. A suspended or churned tenant
# keeps its data and loses its access.
ACTIVE_ORG_STATUSES = frozenset({"trial", "active"})


def normalize_role(role: str | None) -> str:
    return str(role or "").strip().lower()


def is_known_role(role: str | None) -> bool:
    """Whether a role string is one the product actually defines."""
    return normalize_role(role) in GRANTABLE_ROLES


def role_rank(role: str | None) -> int:
    """How far a role reaches. An unknown role reaches nothing."""
    return _ROLE_RANK.get(normalize_role(role), -1)


def may_grant_role(actor_role: str | None, target_role: str | None) -> bool:
    """Whether an org admin at `actor_role` may seat someone at `target_role`.

    Allowed only when the target is a known role at or below the granter's own tier — this
    stops a `partner_admin` from minting `institution_admin` or `owner`. Platform admins do
    not pass through here; they are checked by the caller.
    """
    if not is_known_role(target_role):
        return False
    return role_rank(actor_role) >= role_rank(target_role)


def is_org_admin(role: str | None) -> bool:
    return normalize_role(role) in ORG_ADMIN_ROLES


def an_admin_remains(*, role: str | None, other_admins: int) -> bool:
    """Whether revoking or demoting this member leaves a live administrator.

    `role` is the membership's role before the change and `other_admins` counts
    the live administrators besides it. Without this, an organisation could be
    left with nobody able to seat anyone, and only staff could let them back in.
    """
    return not is_org_admin(role) or other_admins >= 1


def is_institution_admin(role: str | None) -> bool:
    return normalize_role(role) in INSTITUTION_ADMIN_ROLES


def is_assigned_staff(role: str | None) -> bool:
    return normalize_role(role) in ASSIGNED_STAFF_ROLES


def may_lead_review(role: str | None) -> bool:
    """Who writes the lead review of a station: an institution administrator or a lead assessor."""
    return is_institution_admin(role) or normalize_role(role) == LEAD_ASSESSOR_ROLE


def is_trainee(role: str | None) -> bool:
    return normalize_role(role) in END_USER_ROLES


def may_read_org(role: str | None) -> bool:
    """Any member role may read org context; writing is gated per resource."""
    return is_org_admin(role) or is_assigned_staff(role) or is_trainee(role)


def may_run_circuit(role: str | None) -> bool:
    """Who may start, advance and override a live examination.

    Deliberately not `may_read_org`, which includes trainees — a candidate must not be able
    to start, switch or end the circuit they are sitting. "examiner" is a label for the same
    `supervisor` role rather than a role of its own.
    """
    return is_org_admin(role) or is_assigned_staff(role)


def contract_dates_in_order(starts_at: datetime | None, ends_at: datetime | None) -> bool:
    """Whether a contract starts no later than it ends.

    Either date may be open (`None`), and the same day is allowed. A naive
    datetime is read as UTC, so a stored value and a posted one always compare.
    """
    if starts_at is None or ends_at is None:
        return True
    if starts_at.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=UTC)
    if ends_at.tzinfo is None:
        ends_at = ends_at.replace(tzinfo=UTC)
    return starts_at <= ends_at


def contract_lapsed(contract_ends_at: datetime | None, *, now: datetime) -> bool:
    """Whether an organisation's contract has run out.

    No end date means an open-ended arrangement, not a lapsed one. The
    comparison is not strict: a contract that ends at midnight has ended at
    midnight.
    """
    return contract_ends_at is not None and now >= contract_ends_at


def org_active(status: str | None, contract_ends_at: datetime | None, *, now: datetime) -> bool:
    """Whether an organisation may act now: the one org check every gate composes.

    A status that permits access, and a contract that has not run out. The hourly sweep
    turns a lapse into `suspended`; checking the date too makes the lapse bite before it runs.
    """
    permitted = str(status or "").strip().lower() in ACTIVE_ORG_STATUSES
    return permitted and not contract_lapsed(contract_ends_at, now=now)


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
    valid = [membership for membership in memberships if membership.slug]
    if not valid:
        return None
    for raw in preferred_order:
        slug = str(raw or "").strip()
        if not slug:
            continue
        match = next((membership for membership in valid if membership.slug == slug), None)
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
    return next((membership for membership in memberships if membership.slug == slug), None)
