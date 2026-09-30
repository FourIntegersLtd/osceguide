"""Tying `core` to the feature rules it enforces.

`core` never imports a feature, so where a core dependency needs a feature's
answer, the core module declares `bind_x(...)` and this is the one place that
calls it. Feature slices call each other's services directly.

`tests/guards/test_every_seam_is_bound.py` checks both halves — that every
declared `bind_*` is called, and that a built app has each one filled in —
because the failure mode is silence: nobody calls it, and the code that needs
it raises at runtime on whichever route happens to reach it first.
"""

from __future__ import annotations

from app.core.account_status import bind_account_status
from app.core.audience import bind_viewer_audiences
from app.core.auth import bind_password_gate
from app.core.memberships import bind_membership_lookup
from app.core.role_policy import bind_org_access_policy, bind_role_policy
from app.core.tenancy import bind_org_lookup
from app.features.identity.service import account_status, may_call_with_temporary_password
from app.features.roster.service import audiences_for_viewer
from app.features.tenancy.service import (
    is_institution_admin,
    is_org_admin,
    may_read_org,
    may_run_circuit,
    memberships_for_token,
    org_permits_access,
    org_ref_by_slug,
)


def bind_seams() -> None:
    """Called once, by `create_app`."""
    # `identity` needs a user's memberships to stamp a token; core's
    # `get_principal` is where it is read.
    bind_membership_lookup(memberships_for_token)
    # A temporary password reaches only the routes that replace it. The rule is
    # `identity`'s; the enforcement point is core's `get_principal`.
    bind_password_gate(may_call_with_temporary_password)
    # A deactivated account is refused on its next request, not its next
    # refresh. `identity` owns the status; the enforcement point is core's.
    bind_account_status(account_status)
    bind_org_lookup(org_ref_by_slug)
    bind_org_access_policy(org_permits_access)
    # Who can see an institution's or a group's posts. `community`,
    # `marketplace` and `peer_practice` ask through core's audience filter;
    # `roster` and `tenancy` know.
    bind_viewer_audiences(audiences_for_viewer)
    bind_role_policy(
        may_read_org=may_read_org,
        may_run_circuit=may_run_circuit,
        is_org_admin=is_org_admin,
        is_institution_admin=is_institution_admin,
    )
