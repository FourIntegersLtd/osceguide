"""SEC-015: the signed SSO `state` is the only thing tying a callback back to
the sign-in that started it (the platform stores nothing between them — ADR
0004). These prove the guarantees the callback leans on: a state verifies only
when it was minted here, is unexpired, is for the SSO flow, and names the same
organisation the callback claims.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt

from app.core.settings import Settings
from app.features.sso import state as sso_state

# 32+ chars: `Settings` refuses a shorter secret, and HS256 needs a real key.
_SECRET = "s" * 40


def _settings() -> Settings:
    return Settings(jwt_secret=_SECRET, jwt_issuer="osce-guide")


def _now() -> datetime:
    # Real wall-clock time: `verify_state` checks `exp`/`iat` against the
    # system clock, so a fixed future `iat` would read as not-yet-valid.
    return datetime.now(timezone.utc)


def test_a_state_this_platform_minted_verifies_and_yields_its_nonce() -> None:
    settings = _settings()
    state, nonce = sso_state.issue_state(settings, org_slug="kings", now=_now())

    assert sso_state.verify_state(settings, state=state, org_slug="kings") == nonce


def test_a_state_for_another_org_does_not_verify() -> None:
    settings = _settings()
    state, _ = sso_state.issue_state(settings, org_slug="kings", now=_now())

    assert sso_state.verify_state(settings, state=state, org_slug="guys") is None


def test_a_tampered_state_does_not_verify() -> None:
    settings = _settings()
    state, _ = sso_state.issue_state(settings, org_slug="kings", now=_now())

    # Re-signed with a different key: the payload may say "kings", but the
    # signature is not this platform's.
    forged = jwt.encode(
        jwt.decode(state, _SECRET, algorithms=["HS256"], options={"verify_exp": False}),
        "a-different-secret-of-the-right-length!!",
        algorithm="HS256",
    )
    assert sso_state.verify_state(settings, state=forged, org_slug="kings") is None


def test_an_expired_state_does_not_verify() -> None:
    settings = _settings()
    stale = _now() - timedelta(hours=1)
    state, _ = sso_state.issue_state(settings, org_slug="kings", now=stale)

    # An hour later the ten-minute window is long shut.
    assert sso_state.verify_state(settings, state=state, org_slug="kings") is None


def test_an_access_token_shaped_jwt_cannot_pose_as_a_state() -> None:
    """A JWT signed with the same key but without the SSO-state purpose — for
    instance an access token — is not accepted as a state."""
    settings = _settings()
    not_a_state = jwt.encode(
        {
            "iss": "osce-guide",
            "purpose": "access",
            "org_slug": "kings",
            "nonce": "n",
            "exp": int((_now() + timedelta(minutes=5)).timestamp()),
        },
        _SECRET,
        algorithm="HS256",
    )
    assert sso_state.verify_state(settings, state=not_a_state, org_slug="kings") is None
