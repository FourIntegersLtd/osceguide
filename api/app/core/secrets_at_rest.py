"""Encrypting small secrets at rest.

A referrer's bank details (`app.features.growth`'s payout details) are the one
piece of plaintext this platform would otherwise store that a database dump
could turn straight into someone else's money. `encrypt_text`/`decrypt_text`
wrap Fernet — symmetric, authenticated encryption — under one process-wide
key, `settings.payout_details_key`, so a sort code or account number is
unreadable to anyone who only has the database.

This module is deliberately small and generic: it knows nothing about bank
details specifically, so a second feature that needs the same guarantee (a
future secret worth encrypting rather than hashing) can reuse it without a new
key or a new pattern.
"""

from __future__ import annotations

from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.core.settings import Settings, get_settings

# Re-exported so a caller can catch a wrong-key or corrupted-ciphertext error
# without importing `cryptography` itself.
__all__ = ["encrypt_text", "decrypt_text", "PayoutDetailsKeyMissing", "InvalidToken"]


class PayoutDetailsKeyMissing(RuntimeError):
    """Raised when this process has no `PAYOUT_DETAILS_KEY` to encrypt or decrypt with.

    A missing key must never fall back to storing or reading plaintext, so
    every call site fails loudly instead of silently downgrading its own
    security.
    """


@lru_cache
def _cipher_for_key(key: str) -> Fernet:
    """One `Fernet` instance per distinct key value, cached.

    Constructing a `Fernet` validates and base64-decodes the key, which is
    wasted work to repeat on every encrypt or decrypt call in a hot path such
    as the payout settlement queue.
    """
    return Fernet(key.encode("utf-8"))


def _cipher(settings: Settings) -> Fernet:
    """The Fernet cipher for this process's configured key.

    Raises `PayoutDetailsKeyMissing` rather than constructing a cipher from an
    empty string, which `Fernet` would otherwise reject with a less specific
    error.
    """
    if not settings.payout_details_key:
        raise PayoutDetailsKeyMissing(
            "PAYOUT_DETAILS_KEY is not set. Refusing to encrypt or decrypt "
            "bank details rather than doing so in, or reading them as, plaintext."
        )
    return _cipher_for_key(settings.payout_details_key)


def encrypt_text(plaintext: str, *, settings: Settings | None = None) -> str:
    """Encrypt one short string — a sort code, an account number — for storage.

    The result is a self-describing Fernet token: it carries its own
    timestamp and authentication tag, so `decrypt_text` can tell a value
    encrypted under a different key from ordinary corruption.
    """
    cipher = _cipher(settings or get_settings())
    return cipher.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_text(ciphertext: str, *, settings: Settings | None = None) -> str:
    """Decrypt a value `encrypt_text` produced under the same key.

    Raises `cryptography.fernet.InvalidToken` for anything else: a value
    encrypted under a rotated-away key, or one that was never a Fernet token
    at all. Callers do not catch this by default — a payout row that fails to
    decrypt is a configuration problem worth surfacing, not a value to guess
    at or silently drop.
    """
    cipher = _cipher(settings or get_settings())
    return cipher.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
