"""The rules that used to live in the browser bundle."""

from __future__ import annotations

import pytest

from app.features.sso import domain


@pytest.mark.parametrize(
    ("typed", "stored"),
    [
        ("bmj.osceguide.com", "bmj.osceguide.com"),
        ("BMJ.OsceGuide.com", "bmj.osceguide.com"),
        ("  bmj.osceguide.com  ", "bmj.osceguide.com"),
        # People paste URLs into configuration fields.
        ("https://bmj.osceguide.com/", "bmj.osceguide.com"),
        ("http://bmj.osceguide.com/sign-in?x=1", "bmj.osceguide.com"),
        # A port is not part of the identity.
        ("localhost:3000", "localhost"),
        ("bmj.osceguide.com.", "bmj.osceguide.com"),
    ],
)
def test_a_host_is_stored_as_the_header_will_arrive(typed: str, stored: str) -> None:
    assert domain.normalise_host(typed) == stored


@pytest.mark.parametrize("bad", ["", "   ", "not a host", "bmj"])
def test_a_host_that_could_never_match_is_refused(bad: str) -> None:
    with pytest.raises(domain.InvalidBinding):
        domain.normalise_host(bad)


@pytest.mark.parametrize(
    ("typed", "stored"),
    [
        ("nhs.net", "nhs.net"),
        ("NHS.net", "nhs.net"),
        # A whole address is what somebody will paste in.
        ("someone@nhs.net", "nhs.net"),
        ("  @nhs.net ", "nhs.net"),
    ],
)
def test_an_email_domain_is_taken_from_whatever_was_typed(typed: str, stored: str) -> None:
    assert domain.normalise_email_domain(typed) == stored


def test_the_domain_of_a_non_address_is_nothing_to_look_up() -> None:
    assert domain.domain_of("someone@nhs.net") == "nhs.net"
    assert domain.domain_of("someone") is None
    assert domain.domain_of("") is None


def test_sso_only_cannot_be_set_while_sso_is_off() -> None:
    """One checkbox would otherwise lock an institution out of its own account."""
    with pytest.raises(domain.SsoNotConfigurable):
        domain.ensure_configurable(enabled=False, sso_only=True, issuer="https://issuer")


def test_sso_cannot_be_turned_on_without_an_issuer() -> None:
    with pytest.raises(domain.SsoNotConfigurable):
        domain.ensure_configurable(enabled=True, sso_only=False, issuer=None)
    with pytest.raises(domain.SsoNotConfigurable):
        domain.ensure_configurable(enabled=True, sso_only=False, issuer="   ")


def test_an_arrangement_that_holds_together_is_allowed() -> None:
    domain.ensure_configurable(enabled=True, sso_only=True, issuer="https://issuer")
    domain.ensure_configurable(enabled=False, sso_only=False, issuer=None)


def test_a_provider_this_platform_does_not_know_is_refused() -> None:
    assert domain.normalise_provider("CLERK") is domain.Provider.CLERK
    with pytest.raises(domain.InvalidProvider):
        domain.normalise_provider("okta")


def test_a_button_with_no_words_on_it_falls_back_to_the_provider_default() -> None:
    assert domain.sign_in_label(None, domain.Provider.ENTRA) == "Sign in with Microsoft"
    assert domain.sign_in_label("   ", domain.Provider.CLERK) == "Sign in with your organisation"
    assert domain.sign_in_label("Sign in with BMJ", domain.Provider.CLERK) == "Sign in with BMJ"
