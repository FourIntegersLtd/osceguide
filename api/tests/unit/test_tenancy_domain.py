"""Authorisation rules, ported from the legacy b2b policy as the oracle.

Source: `backend/b2b-api/app/features/auth/policy.py` and `jwt_claims.py`.
These assertions are the behaviour that must survive the replatform; the
product vocabulary is stripped but the decisions are identical. Anything here
that changes is a deliberate product decision, not a refactor.
"""

from __future__ import annotations

import pytest

from app.features.tenancy import domain

# --------------------------------------------------------------------------
# Role predicates (oracle: policy.py:19-64)
# --------------------------------------------------------------------------


@pytest.mark.parametrize("role", ["owner", "admin", "institution_admin", "partner_admin"])
def test_org_admin_roles(role: str) -> None:
    assert domain.is_org_admin(role)


@pytest.mark.parametrize("role", ["supervisor", "trainee", "practice_user", "", None, "nonsense"])
def test_non_admin_roles_are_not_org_admin(role: str | None) -> None:
    assert not domain.is_org_admin(role)


def test_platform_admin_is_not_an_org_admin() -> None:
    """Oracle: policy.py:27-28. A console admin does not inherit org powers."""
    assert not domain.is_org_admin("platform_admin")


@pytest.mark.parametrize("role", ["owner", "admin", "institution_admin"])
def test_institution_admin_is_the_narrower_set(role: str) -> None:
    assert domain.is_institution_admin(role)


def test_partner_admin_is_an_org_admin_but_not_an_institution_admin() -> None:
    """The distinction that gates candidate-result sign-off."""
    assert domain.is_org_admin("partner_admin")
    assert not domain.is_institution_admin("partner_admin")


@pytest.mark.parametrize("role", ["trainee", "practice_user"])
def test_end_user_roles(role: str) -> None:
    assert domain.is_trainee(role)


def test_supervisor_is_assigned_staff_not_a_trainee() -> None:
    assert domain.is_assigned_staff("supervisor")
    assert not domain.is_trainee("supervisor")


@pytest.mark.parametrize(
    "role", ["owner", "admin", "institution_admin", "partner_admin", "supervisor", "trainee", "practice_user"]
)
def test_every_member_role_may_read_org_context(role: str) -> None:
    """Oracle: policy.py check_org_access — read access is broad, write access is not."""
    assert domain.may_read_org(role)


@pytest.mark.parametrize("role", ["platform_admin", "", None, "stranger"])
def test_non_members_may_not_read_org_context(role: str | None) -> None:
    assert not domain.may_read_org(role)


@pytest.mark.parametrize("raw", ["  Owner  ", "OWNER", "Owner"])
def test_roles_are_normalised_before_comparison(raw: str) -> None:
    """Oracle: policy.py normalize_role strips and lowercases."""
    assert domain.is_org_admin(raw)


# --------------------------------------------------------------------------
# Active workspace selection (oracle: jwt_claims.pick_default_membership)
# --------------------------------------------------------------------------


def m(slug: str, role: str = "admin") -> domain.MembershipRef:
    return domain.MembershipRef(org_slug=slug, role=role)


def test_default_workspace_follows_the_users_org_order() -> None:
    memberships = [m("beta"), m("alpha")]
    assert domain.pick_default_workspace(memberships, ["alpha", "beta"]).org_slug == "alpha"


def test_default_workspace_falls_back_to_the_first_membership() -> None:
    """An org order that matches nothing must not leave the user with no workspace."""
    memberships = [m("beta"), m("alpha")]
    assert domain.pick_default_workspace(memberships, ["gone"]).org_slug == "beta"


def test_default_workspace_ignores_blank_slugs_in_the_order() -> None:
    memberships = [m("beta"), m("alpha")]
    assert domain.pick_default_workspace(memberships, ["", "  ", "alpha"]).org_slug == "alpha"


def test_no_memberships_means_no_workspace() -> None:
    assert domain.pick_default_workspace([], ["alpha"]) is None


# --------------------------------------------------------------------------
# Switching workspace (oracle: jwt_claims.apply_active_workspace)
# --------------------------------------------------------------------------


def test_switching_to_a_membership_you_hold_resolves_it() -> None:
    memberships = [m("alpha", "trainee"), m("beta", "owner")]
    assert domain.resolve_workspace(memberships, "beta").role == "owner"


def test_switching_to_an_org_you_are_not_in_is_refused() -> None:
    """Oracle: apply_active_workspace returns None, which the route turns into 403."""
    assert domain.resolve_workspace([m("alpha")], "beta") is None


def test_switching_to_a_blank_slug_is_refused() -> None:
    assert domain.resolve_workspace([m("alpha")], "   ") is None


# --------------------------------------------------------------------------
# Organisation status (oracle: b2b org_core.py:12-13)
# --------------------------------------------------------------------------


@pytest.mark.parametrize("status", ["trial", "active"])
def test_only_trial_and_active_organisations_permit_access(status: str) -> None:
    assert domain.org_permits_access(status)


@pytest.mark.parametrize("status", ["inactive", "suspended", "churned", "", None])
def test_every_other_organisation_status_refuses_access(status: str | None) -> None:
    assert not domain.org_permits_access(status)
