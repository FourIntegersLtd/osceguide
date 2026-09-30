"""Who must use a second factor. One assertion per branch of the rule."""

from __future__ import annotations

from app.features.identity.domain import STAFF_MFA_EXEMPT_ROLES, MfaMembership, mfa_required_reason
from app.features.tenancy.domain import END_USER_ROLES


def test_exempt_roles_are_the_end_user_roles() -> None:
    assert STAFF_MFA_EXEMPT_ROLES == END_USER_ROLES


def test_a_platform_admin_must_use_mfa() -> None:
    assert mfa_required_reason(is_platform_admin=True, memberships=[]) == "platform_admin"


def test_a_platform_admin_must_use_mfa_even_as_a_trainee() -> None:
    membership = MfaMembership(role="trainee", org_requires_staff_mfa=True)
    assert mfa_required_reason(is_platform_admin=True, memberships=[membership]) == "platform_admin"


def test_a_supervisor_in_an_org_that_requires_mfa_must_use_it() -> None:
    membership = MfaMembership(role="supervisor", org_requires_staff_mfa=True)
    assert mfa_required_reason(is_platform_admin=False, memberships=[membership]) == "org_policy"


def test_an_institution_admin_in_an_org_that_requires_mfa_must_use_it() -> None:
    membership = MfaMembership(role="institution_admin", org_requires_staff_mfa=True)
    assert mfa_required_reason(is_platform_admin=False, memberships=[membership]) == "org_policy"


def test_a_trainee_in_an_org_that_requires_mfa_need_not() -> None:
    membership = MfaMembership(role="trainee", org_requires_staff_mfa=True)
    assert mfa_required_reason(is_platform_admin=False, memberships=[membership]) is None


def test_a_practice_user_in_an_org_that_requires_mfa_need_not() -> None:
    membership = MfaMembership(role="practice_user", org_requires_staff_mfa=True)
    assert mfa_required_reason(is_platform_admin=False, memberships=[membership]) is None


def test_staff_in_an_org_that_does_not_require_mfa_need_not() -> None:
    membership = MfaMembership(role="supervisor", org_requires_staff_mfa=False)
    assert mfa_required_reason(is_platform_admin=False, memberships=[membership]) is None


def test_someone_with_no_membership_need_not() -> None:
    assert mfa_required_reason(is_platform_admin=False, memberships=[]) is None
