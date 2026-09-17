"""Oracle: `b2b-api/tests/test_jwt_claims.py`.

Which workspace a token lands in, and which role it carries there. Ported
because getting it wrong is not a cosmetic bug: a user dropped into the wrong
workspace sees another organisation's screens, and a user dropped into *no*
workspace gets 403 from every org-scoped route while plainly being a member.

The legacy helpers were `jwt_claims.pick_default_membership(memberships,
priority_slugs)` and `jwt_claims.effective_api_role(active_role, base_role)`.
Both are ported with the product vocabulary stripped, per CONTRIBUTING step 4.

One legacy behaviour is deliberately **not** carried over, and it is recorded
at the bottom of this file rather than silently dropped: b2b prioritised the
`osce_guide` *organisation* so a platform administrator landed in the console.
Platform admin is a flag on the user here (`users.is_platform_admin`), not a
membership in an organisation, so there is no platform org to prefer. The
preference mechanism itself is kept and tested, because organisations with a
preferred order are still a real case.
"""

from __future__ import annotations

import uuid

from app.core.auth import Membership, Principal
from app.features.tenancy import service
from app.features.tenancy.domain import MembershipRef, pick_default_workspace

INSTITUTION = MembershipRef(org_slug="asterix", role="institution_admin", org_type="institution")
PLATFORM = MembershipRef(org_slug="osce_guide", role="platform_admin", org_type="platform")


def test_a_preferred_slug_wins_over_the_first_membership() -> None:
    """Oracle: `pick_default_membership(memberships, ["osce_guide"])`.

    Order of the memberships does not decide it; the preference does.
    """
    picked = pick_default_workspace([INSTITUTION, PLATFORM], preferred_order=["osce_guide"])
    assert picked is not None
    assert picked.slug == "osce_guide"
    assert picked.role == "platform_admin"


def test_a_preference_naming_nothing_falls_back_to_the_first() -> None:
    """Oracle: `pick_default_membership(memberships, ["missing-org"])`.

    Not None. Somebody who is plainly a member must not land nowhere, because
    "no active workspace" makes every org-scoped route answer 403.
    """
    picked = pick_default_workspace([INSTITUTION], preferred_order=["missing-org"])
    assert picked is not None
    assert picked.slug == "asterix"


def test_somebody_in_no_organisation_has_no_workspace() -> None:
    """A consumer. Distinct from the case above: there is nothing to fall back to."""
    assert pick_default_workspace([], preferred_order=["osce_guide"]) is None


def test_a_blank_preference_is_skipped_rather_than_matched() -> None:
    """An empty slug in the preference list must not match a blank membership."""
    picked = pick_default_workspace([INSTITUTION, PLATFORM], preferred_order=["", "osce_guide"])
    assert picked is not None
    assert picked.slug == "osce_guide"


def test_the_workspace_a_fresh_token_lands_in_is_the_first_membership() -> None:
    """The wiring, not the rule: `service.default_workspace_for` is what `main.py` binds.

    Three copies of `memberships[0]` used to decide this while the rule had no
    caller at all, so the rule and the wiring are tested separately — a rule
    that is right and unwired is what the 16 September audit was about.
    """
    org_id = uuid.uuid4()
    memberships = [
        Membership(org_id=org_id, org_slug="asterix", role="institution_admin"),
        Membership(org_id=uuid.uuid4(), org_slug="kings", role="owner"),
    ]
    assert service.default_workspace_for(memberships) == "asterix"


def test_a_consumer_token_lands_in_no_workspace() -> None:
    assert service.default_workspace_for([]) is None


def test_the_active_membership_decides_the_role_not_the_account() -> None:
    """Oracle: `effective_api_role(active_role, base_role)`.

    b2b returned the active membership's role where there was one and the
    account's otherwise. Here the active membership *is* the only source of a
    role — `capabilities_for` reads it and nothing else — so the oracle is
    expressed as what the capabilities come out as.
    """
    org_id = uuid.uuid4()
    principal = Principal(
        user_id=uuid.uuid4(),
        email="two-hats@example.com",
        memberships=(
            Membership(org_id=org_id, org_slug="asterix", role="institution_admin"),
            Membership(org_id=uuid.uuid4(), org_slug="kings", role="trainee"),
        ),
        active_org_slug="kings",
    )
    capabilities = service.capabilities_for(principal)

    assert capabilities.active_role == "trainee"
    assert capabilities.can["read_org"] is True
    # Being an admin somewhere else does not make you one here.
    assert capabilities.can["manage_team"] is False
    assert capabilities.can["sign_off_results"] is False


def test_platform_administration_is_an_account_flag_not_a_membership() -> None:
    """What replaced b2b's `osce_guide` organisation.

    b2b made somebody a platform administrator by putting them in an org named
    `osce_guide` with the role `platform_admin`, which is why its default
    workspace had to prefer that slug. Here it is a column on the user, so a
    platform administrator with no membership at all still administers the
    platform — and inherits nothing inside any organisation, which is the half
    the legacy policy is emphatic about.
    """
    principal = Principal(
        user_id=uuid.uuid4(),
        email="root@osceguide.com",
        memberships=(),
        active_org_slug=None,
        is_platform_admin=True,
    )
    capabilities = service.capabilities_for(principal)

    assert capabilities.can["administer_platform"] is True
    assert capabilities.can["manage_team"] is False
    assert capabilities.can["sign_off_results"] is False
    assert capabilities.active_role is None
