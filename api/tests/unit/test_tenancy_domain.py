"""Authorisation rules, ported from the legacy b2b policy as the oracle.

Source: `backend/b2b-api/app/features/auth/policy.py` and `jwt_claims.py`.
These assertions are the behaviour that must survive the replatform; the
product vocabulary is stripped but the decisions are identical. Anything here
that changes is a deliberate product decision, not a refactor.
"""

from __future__ import annotations

from datetime import UTC, datetime

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


@pytest.mark.parametrize("role", ["owner", "admin", "institution_admin", "partner_admin", "supervisor"])
def test_staff_may_run_a_circuit(role: str) -> None:
    """Starting, advancing and overriding an examination is a staff act."""
    assert domain.may_run_circuit(role)


@pytest.mark.parametrize("role", ["trainee", "practice_user", "platform_admin", "", None, "stranger"])
def test_a_candidate_may_not_run_the_circuit_they_are_sitting(role: str | None) -> None:
    """The rule `may_read_org` could not express: reading is broad, running is not.

    Every run route used to take `may_read_org`, which includes trainees — so a
    candidate could start, advance and end their own examination.
    """
    assert not domain.may_run_circuit(role)


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


def day(d: int, *, tz: bool = True) -> datetime:
    return datetime(2027, 1, d, tzinfo=UTC if tz else None)


@pytest.mark.parametrize(
    ("starts_at", "ends_at", "in_order"),
    [
        (day(2), day(1), False),
        (day(1), day(1), True),
        (day(1), day(2), True),
        (day(2), None, True),
        (None, day(1), True),
        (None, None, True),
        (day(2, tz=False), day(1), False),
    ],
)
def test_a_contract_may_not_start_after_it_ends(
    starts_at: datetime | None, ends_at: datetime | None, in_order: bool
) -> None:
    assert domain.contract_dates_in_order(starts_at, ends_at) is in_order


def test_the_last_administrator_cannot_be_removed() -> None:
    assert domain.an_admin_remains(role="owner", other_admins=0) is False


def test_an_administrator_with_a_colleague_can_be_removed() -> None:
    assert domain.an_admin_remains(role="owner", other_admins=1) is True


def test_removing_a_non_administrator_never_needs_another_admin() -> None:
    assert domain.an_admin_remains(role="supervisor", other_admins=0) is True
