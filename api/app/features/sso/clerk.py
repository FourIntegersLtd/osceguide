"""The Clerk adapter behind `core.ports.SsoBroker`.

Over `httpx` against Clerk's Backend API rather than through an SDK, the way
`billing/checkout.py` talks to Stripe: verify the session token the callback is
handed, then fetch the user it belongs to. The retiring consumer backend did
the same in its `clerk_service`; this is that flow on the platform's footing —
no Firestore, no cookie, and the platform issues the session (ADR 0004).

Only the session-token path is ported. The dev-mode `__clerk_db_jwt` exchange
— resolving a database JWT through the Frontend API — was a development
convenience for a browser that had not finished signing in, and is deliberately
not here; a production callback arrives with a session token.
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
    first = str(clerk_user.get("first_name") or "").strip()
    last = str(clerk_user.get("last_name") or "").strip()
    return f"{first} {last}".strip() or str(clerk_user.get("username") or "")


class ClerkBroker:
    """Verifies a Clerk session and builds the sign-in URL for a frontend domain."""

    def __init__(self, secret_key: str) -> None:
        self._secret_key = secret_key

    def sign_in_url(self, *, redirect_url: str, issuer: str | None) -> str:
        """The organisation's Clerk sign-in page, told where to come back to.

        `issuer` is the Clerk frontend domain stored on the organisation's
        configuration. Without it there is no sign-in page to send anybody to,
        so this refuses rather than guessing a domain.
        """
        domain = (issuer or "").strip()
        if not domain:
            raise SsoBrokerUnavailable("This organisation has no Clerk frontend domain configured")
        return f"https://{domain}/sign-in?redirect_url={quote(redirect_url, safe='')}"

    async def verify(self, *, token: str) -> SsoIdentity | None:
        payload = _decode_payload(token)
        if payload is None:
            return None
        session_id = str(payload.get("sid") or "").strip()
        if not session_id:
            return None
        headers = {"Authorization": f"Bearer {self._secret_key}"}
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
                verified = await client.post(
                    f"{CLERK_API_BASE}/sessions/{session_id}/verify", headers=headers, json={"token": token}
                )
                if verified.status_code >= 400:
                    log.warning("clerk refused a session", status=verified.status_code)
                    return None
                user_id = str(verified.json().get("user_id") or payload.get("sub") or "").strip()
                if not user_id:
                    return None
                fetched = await client.get(f"{CLERK_API_BASE}/users/{user_id}", headers=headers)
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
    """The adapter, or a refusal. Never a silent no-op.

    A deployment with no secret key cannot verify anybody, and `CLERK_SECRET_KEY`
    is deliberately not one of the required ten — so this is a real state a
    running process can be in, and it says so rather than accepting an
    unverified token.
    """
    if not settings.clerk_secret_key.strip():
        raise SsoBrokerUnavailable("CLERK_SECRET_KEY is not set, so this deployment cannot offer SSO")
    return ClerkBroker(settings.clerk_secret_key)
