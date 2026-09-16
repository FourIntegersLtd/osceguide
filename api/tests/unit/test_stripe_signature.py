"""Verifying that a webhook really came from Stripe.

The scheme is documented and simple: the header carries a timestamp and one or
more HMAC-SHA256 signatures over `timestamp.payload`, keyed by the signing
secret. Implemented here rather than taken from the SDK so it can be tested
without an account, and so the tolerance and the comparison are visible.
"""

from __future__ import annotations

import hashlib
import hmac
import time

import pytest

from app.features.billing import signature

SECRET = "whsec_test_secret"  # noqa: S105 - a test fixture, not a credential
PAYLOAD = b'{"id":"evt_1","type":"checkout.session.completed"}'


def sign(payload: bytes, secret: str, timestamp: int) -> str:
    signed = f"{timestamp}.".encode() + payload
    mac = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={mac}"


def test_a_genuine_signature_verifies() -> None:
    now = int(time.time())
    signature.verify(PAYLOAD, sign(PAYLOAD, SECRET, now), secret=SECRET, now=now)


def test_a_forged_signature_is_refused() -> None:
    now = int(time.time())
    header = sign(PAYLOAD, "whsec_someone_elses", now)
    with pytest.raises(signature.InvalidSignature):
        signature.verify(PAYLOAD, header, secret=SECRET, now=now)


def test_a_tampered_payload_is_refused() -> None:
    """The point of the whole exercise: the body cannot be changed in flight."""
    now = int(time.time())
    header = sign(PAYLOAD, SECRET, now)
    with pytest.raises(signature.InvalidSignature):
        signature.verify(b'{"id":"evt_1","amount":999999}', header, secret=SECRET, now=now)


def test_an_old_signature_is_refused() -> None:
    """Replay protection. Without the tolerance, a captured webhook works forever."""
    now = int(time.time())
    header = sign(PAYLOAD, SECRET, now - signature.TOLERANCE_SECONDS - 60)
    with pytest.raises(signature.InvalidSignature):
        signature.verify(PAYLOAD, header, secret=SECRET, now=now)


def test_a_signature_inside_the_tolerance_is_accepted() -> None:
    now = int(time.time())
    header = sign(PAYLOAD, SECRET, now - signature.TOLERANCE_SECONDS + 10)
    signature.verify(PAYLOAD, header, secret=SECRET, now=now)


def test_a_future_timestamp_within_tolerance_is_accepted() -> None:
    """Clocks drift; a few seconds ahead is not an attack."""
    now = int(time.time())
    signature.verify(PAYLOAD, sign(PAYLOAD, SECRET, now + 5), secret=SECRET, now=now)


def test_several_signatures_pass_if_any_matches() -> None:
    """Stripe sends more than one during a secret rotation."""
    now = int(time.time())
    good = sign(PAYLOAD, SECRET, now).split("v1=")[1]
    header = f"t={now},v1=deadbeef,v1={good}"
    signature.verify(PAYLOAD, header, secret=SECRET, now=now)


@pytest.mark.parametrize("header", ["", "nonsense", "t=abc,v1=x", "v1=onlysig", "t=123"])
def test_a_malformed_header_is_refused(header: str) -> None:
    with pytest.raises(signature.InvalidSignature):
        signature.verify(PAYLOAD, header, secret=SECRET, now=int(time.time()))


def test_an_unconfigured_secret_refuses_everything() -> None:
    """Fails closed. An unset secret must not mean "accept anything", which is
    how both legacy worker guards behave."""
    now = int(time.time())
    with pytest.raises(signature.SigningSecretMissing):
        signature.verify(PAYLOAD, sign(PAYLOAD, SECRET, now), secret="", now=now)
