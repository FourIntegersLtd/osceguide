"""Verifying that a webhook really came from Stripe.

Implemented by hand rather than via the SDK: testable without an account, and the constant-time
comparison and replay tolerance are visible rather than assumed.

The scheme: the `Stripe-Signature` header carries `t=<unix seconds>` and one or more
`v1=<hex>` HMAC-SHA256 digests over `"{timestamp}.{raw body}"`, keyed by the signing secret.
"""

from __future__ import annotations

import hashlib
import hmac

# Stripe's own default. Past this a captured webhook is refused, so a recorded
# request cannot be replayed indefinitely.
TOLERANCE_SECONDS = 300

SCHEME = "v1"


class InvalidSignature(Exception):
    pass


class SigningSecretMissing(Exception):
    """No secret configured. Raised rather than passing, so an unset variable cannot quietly
    mean "accept anything"."""


def _parse(header: str) -> tuple[int, list[str]]:
    timestamp: int | None = None
    signatures: list[str] = []
    for part in (header or "").split(","):
        key, _, value = part.strip().partition("=")
        if key == "t":
            try:
                timestamp = int(value)
            except ValueError as exc:
                raise InvalidSignature("The signature timestamp is not a number.") from exc
        elif key == SCHEME and value:
            signatures.append(value)
    if timestamp is None or not signatures:
        raise InvalidSignature("The signature header is malformed.")
    return timestamp, signatures


def verify(payload: bytes, header: str, *, secret: str, now: int) -> None:
    """Raise unless `payload` was signed by `secret` recently enough."""
    if not secret:
        raise SigningSecretMissing("No Stripe signing secret is configured; webhooks cannot be verified.")

    timestamp, signatures = _parse(header)
    if abs(now - timestamp) > TOLERANCE_SECONDS:
        # Signed too long ago — or too far in the future, which a real sender
        # cannot manage but a clock skew of minutes would suggest.
        raise InvalidSignature("That signature is outside the tolerance window.")

    expected = hmac.new(secret.encode(), f"{timestamp}.".encode() + payload, hashlib.sha256).hexdigest()
    # `compare_digest`, so a wrong signature takes the same time to reject
    # whatever it got right. Any match passes: Stripe sends several during a
    # secret rotation.
    if not any(hmac.compare_digest(expected, candidate) for candidate in signatures):
        raise InvalidSignature("That signature does not match the payload.")
