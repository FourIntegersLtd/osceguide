"""The Clerk adapter behind `core.ports.SsoBroker`.

Over `httpx` against Clerk's Backend API rather than through an SDK, the way
`billing/checkout.py` talks to Stripe: verify the session token the callback
is handed, then fetch the user it belongs to. The platform issues its own
session (ADR 0004).

Only the session-token path is supported; a production callback always
arrives with one.
"""

from __future__ import annotations

import base64
import json
from typing import Any
from urllib.parse import quote

import httpx

from app.core.logging import get_logger
from app.core.ports import SsoBrokerUnavailable, SsoIdentity
from app.core.settings import Settings

log = get_logger(__name__)

CLERK_API_BASE = "https://api.clerk.com/v1"
TIMEOUT_SECONDS = 15.0


def _decode_payload(token: str) -> dict[str, Any] | None:
    """Read a JWT's payload without verifying it, to learn the session id.

    The signature is checked by Clerk's verify endpoint, not here; decoding is
    only to know *which* session to ask about. A token that is not three
    dot-separated segments is not a JWT and verifies as nothing.
    """
    parts = token.split(".")
    if len(parts) != 3:
        return None
    segment = parts[1]
    segment += "=" * (-len(segment) % 4)
    try:
        decoded = json.loads(base64.urlsafe_b64decode(segment))
    except (ValueError, json.JSONDecodeError):
        return None
    return decoded if isinstance(decoded, dict) else None


def _primary_email(clerk_user: dict[str, Any]) -> str | None:
    """The address Clerk marks primary, or the first one it has, or None for
    an account with none — which this slice treats as unusable rather than
    guessing."""
    addresses = clerk_user.get("email_addresses") or []
    primary_id = str(clerk_user.get("primary_email_address_id") or "").strip()
    if primary_id:
        for entry in addresses:
            if entry.get("id") == primary_id and entry.get("email_address"):
                return str(entry["email_address"])
    for entry in addresses:
        if entry.get("email_address"):
            return str(entry["email_address"])
    return None


def _full_name(clerk_user: dict[str, Any]) -> str:
    """First and last name joined, falling back to the username, or an
    empty string for an account with none of the three."""
    first = str(clerk_user.get("first_name") or "").strip()
    last = str(clerk_user.get("last_name") or "").strip()
    return f"{first} {last}".strip() or str(clerk_user.get("username") or "")


class ClerkBroker:
    """Verifies a Clerk session and builds the sign-in URL for a frontend domain."""

    def __init__(self, secret_key: str) -> None:
        self._secret_key = secret_key

    def sign_in_url(
        self, *, redirect_url: str, issuer: str | None, state: str | None = None, nonce: str | None = None
    ) -> str:
        """The organisation's Clerk sign-in page, told where to come back to.

        `issuer` is the Clerk frontend domain stored on the organisation's
        configuration. Without it there is no sign-in page to send anybody to,
        so this refuses rather than guessing a domain.

        `state`/`nonce` (SEC-015) belong to the OIDC code flow; Clerk's own
        session verification does not carry them, so they are ignored here.
        """
        del state, nonce
        domain = (issuer or "").strip()
        if not domain:
            raise SsoBrokerUnavailable("This organisation has no Clerk frontend domain configured")
        return f"https://{domain}/sign-in?redirect_url={quote(redirect_url, safe='')}"

    async def verify(
        self, *, token: str, issuer: str | None = None, expected_nonce: str | None = None
    ) -> SsoIdentity | None:
        """Ask Clerk whether this session token is real, and fetch who it
        belongs to.

        Refuses (returns None) rather than raises for anything Clerk itself
        calls a bad token or session: an expired, revoked or forged token, or
        one for a user Clerk cannot then find, all look identical to the
        caller — "this token does not prove anyone signed in". A network or
        server failure talking to Clerk raises `SsoBrokerUnavailable`
        instead, since that is not a verdict on the token at all.
        """
        # One secret key verifies every partner's session; `issuer` (a
        # Clerk frontend domain) is only needed to build the sign-in URL, and
        # `expected_nonce` belongs to the OIDC flow Clerk does not run.
        del issuer, expected_nonce
        token_claims = _decode_payload(token)
        if token_claims is None:
            return None
        session_id = str(token_claims.get("sid") or "").strip()
        if not session_id:
            return None
        # SEC-019: `sid` comes from a JWT whose signature is not verified until
        # the call below, so it is untrusted here. Encode it before splicing it
        # into the request path so a crafted `sid` (a `/`, `?`, `#` or `..`)
        # cannot reshape the URL the org's Clerk secret key is sent to.
        session_segment = quote(session_id, safe="")
        verify_url = f"{CLERK_API_BASE}/sessions/{session_segment}/verify"
        headers = {"Authorization": f"Bearer {self._secret_key}"}
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
                verified = await client.post(verify_url, headers=headers, json={"token": token})
                if verified.status_code >= 400:
                    log.warning("clerk refused a session", status=verified.status_code)
                    return None
                user_id = str(verified.json().get("user_id") or token_claims.get("sub") or "").strip()
                if not user_id:
                    return None
                user_url = f"{CLERK_API_BASE}/users/{quote(user_id, safe='')}"
                fetched = await client.get(user_url, headers=headers)
        except httpx.HTTPError as exc:
            raise SsoBrokerUnavailable(f"could not reach Clerk: {exc}") from exc

        if fetched.status_code >= 400:
            log.warning("clerk could not fetch a user", status=fetched.status_code)
            return None
        clerk_user = fetched.json()
        email = _primary_email(clerk_user)
        if not email:
            return None
        return SsoIdentity(
            email=email, name=_full_name(clerk_user), subject=str(clerk_user.get("id") or user_id)
        )


def build_clerk_broker(settings: Settings) -> ClerkBroker:
    """The adapter, or a refusal — never a silent no-op that accepts an
    unverified token."""
    if not settings.clerk_secret_key.strip():
        raise SsoBrokerUnavailable("CLERK_SECRET_KEY is not set, so this deployment cannot offer SSO")
    return ClerkBroker(settings.clerk_secret_key)
