"""Credential and session rules, with the legacy behaviour named explicitly.

Where this departs from the legacy backends it is deliberate and the test says
so: b2b hashed passwords with unsalted SHA-256 and issued 30-day tokens with no
refresh and no revocation, which is the thing being replaced, not preserved.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.features.identity import domain

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


# --------------------------------------------------------------------------
# Email identity
# --------------------------------------------------------------------------


@pytest.mark.parametrize("raw", ["Alice@Example.com", "  alice@example.com  ", "ALICE@EXAMPLE.COM"])
def test_email_is_normalised_to_one_identity(raw: str) -> None:
    """One person is one row. The migration merges five legacy user stores on this."""
    assert domain.normalize_email(raw) == "alice@example.com"


# --------------------------------------------------------------------------
# Password policy
# --------------------------------------------------------------------------


def test_a_password_must_be_long_enough() -> None:
    with pytest.raises(domain.WeakPassword):
        domain.validate_password("short1!")


def test_a_password_may_not_be_only_one_character_class() -> None:
    with pytest.raises(domain.WeakPassword):
        domain.validate_password("aaaaaaaaaaaaaaa")


def test_a_reasonable_password_is_accepted() -> None:
    domain.validate_password("correct horse battery")


def test_whitespace_is_not_stripped_from_a_password() -> None:
    """Trimming a password silently changes it and breaks the next sign-in."""
    assert domain.password_for_hashing(" pass phrase ") == " pass phrase "


# --------------------------------------------------------------------------
# Refresh token rotation and reuse detection
# --------------------------------------------------------------------------


def chain() -> domain.RefreshChain:
    return domain.RefreshChain(chain_id="c1", current_token_id="t1", expires_at=NOW + timedelta(days=30))


def test_presenting_the_current_token_rotates_it() -> None:
    decision = domain.use_refresh_token(chain(), presented_token_id="t1", now=NOW)
    assert decision.accepted and decision.revoke_chain is False


def test_presenting_an_already_rotated_token_revokes_the_whole_chain() -> None:
    """Reuse means the token leaked. Refusing this one request is not enough."""
    decision = domain.use_refresh_token(chain(), presented_token_id="t0", now=NOW)
    assert not decision.accepted
    assert decision.revoke_chain is True
    assert decision.reason == "reuse_detected"


def test_an_expired_chain_is_refused_without_revoking_anything() -> None:
    decision = domain.use_refresh_token(chain(), presented_token_id="t1", now=NOW + timedelta(days=31))
    assert not decision.accepted
    assert decision.revoke_chain is False
    assert decision.reason == "expired"


def test_a_revoked_chain_is_refused() -> None:
    revoked = domain.RefreshChain(
        chain_id="c1", current_token_id="t1", expires_at=NOW + timedelta(days=30), revoked_at=NOW
    )
    decision = domain.use_refresh_token(revoked, presented_token_id="t1", now=NOW)
    assert not decision.accepted
    assert decision.reason == "revoked"


# --------------------------------------------------------------------------
# Forced password change
# --------------------------------------------------------------------------


def test_a_provisioned_user_may_only_change_their_password() -> None:
    """Institutions invite people with a temporary password; it must not be usable
    to roam the API until it has been replaced."""
    assert domain.may_call(must_change_password=True, route="auth.change_password")
    assert domain.may_call(must_change_password=True, route="me.read")
    assert not domain.may_call(must_change_password=True, route="sittings.list")


def test_an_ordinary_user_may_call_anything() -> None:
    assert domain.may_call(must_change_password=False, route="sittings.list")
