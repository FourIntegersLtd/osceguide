"""The port for an external identity broker.

A slice depends on this Protocol, never on a provider's SDK or HTTP API.
Production wires the Clerk adapter (`features/sso/clerk.py`); tests wire
`FakeSsoBroker`. It lives beside the other ports rather than inside `ports.py`
only because that file reached its cap, and is re-exported from there so every
caller keeps one import for "a port".

The platform owns `users` and issues its own tokens (ADR 0004); a broker only
answers "who is this, and did they really sign in". Clerk is the first adapter
and the one the retiring consumer backend brokered through; direct OIDC to
Entra would be another, behind the same Protocol.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


class SsoBrokerUnavailable(Exception):
    """The broker is not configured, could not be reached, or refused.

    A plain exception rather than an `AppError`: this is the port's vocabulary,
    and the slice that calls it translates it into the error it answers with,
    the way `billing` turns `CheckoutUnavailable` into `checkout_failed`.
    """


@dataclass(frozen=True)
class SsoIdentity:
    """Who the broker vouched for.

    `subject` is the broker's own stable id for the person — a Clerk user id —
    stored against the platform user in `user_identities`, so a second sign-in
    finds the same account even if the address on it has since changed.
    """

    email: str
    name: str
    subject: str


@runtime_checkable
class SsoBroker(Protocol):
    """An external identity provider this platform delegates verification to."""

    def sign_in_url(self, *, redirect_url: str, issuer: str | None) -> str:
        """Where to send the browser to start signing in.

        `issuer` is the organisation's stored broker identity — for Clerk, its
        frontend domain. Raises `SsoBrokerUnavailable` rather than returning a
        URL it is not sure of: sending somebody to a broken sign-in is worse
        than telling them it did not work.
        """
        ...

    async def verify(self, *, token: str) -> SsoIdentity | None:
        """Check a token the broker handed back, and say who it is for.

        Returns None when the token does not verify; raises
        `SsoBrokerUnavailable` when the broker could not be reached. Never
        returns an identity it is not sure of — an unverified token must not
        become a session.
        """
        ...
