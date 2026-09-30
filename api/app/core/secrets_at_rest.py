"""Encrypting small secrets at rest.

`encrypt_text`/`decrypt_text` wrap Fernet — symmetric, authenticated
encryption — under a key the caller passes in. Two features use it today,
each with its own key: a referrer's bank details (`PAYOUT_DETAILS_KEY`) and
a TOTP shared secret (`MFA_SECRET_KEY`). The module does not know which
secret it is holding, so a new caller picks a key rather than copying this
file.
"""

from __future__ import annotations

from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

# Re-exported so a caller can catch a wrong-key or corrupted-ciphertext error
# without importing `cryptography` itself.
__all__ = ["encrypt_text", "decrypt_text", "SecretKeyMissing", "InvalidToken"]


class SecretKeyMissing(RuntimeError):
    """Raised when a caller asks to encrypt or decrypt with an empty key.

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


def _cipher(key: str) -> Fernet:
    """The Fernet cipher for this key.

    Raises `SecretKeyMissing` rather than constructing a cipher from an empty
    string, which `Fernet` would otherwise reject with a less specific error.
    """
    if not key:
        raise SecretKeyMissing(
            "Refusing to encrypt or decrypt with an empty key rather than storing plaintext."
        )
    return _cipher_for_key(key)


def encrypt_text(plaintext: str, *, key: str) -> str:
    """Encrypt one short string for storage under `key`.

    The result is a self-describing Fernet token: it carries its own
    timestamp and authentication tag, so `decrypt_text` can tell a value
    encrypted under a different key from ordinary corruption.
    """
    return _cipher(key).encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_text(ciphertext: str, *, key: str) -> str:
    """Decrypt a value `encrypt_text` produced under the same key.

    Raises `cryptography.fernet.InvalidToken` for anything else: a value
    encrypted under a rotated-away key, or one that was never a Fernet token
    at all. Callers do not catch this by default — a row that fails to
    decrypt is a configuration problem worth surfacing, not a value to guess
    at or silently drop.
    """
    return _cipher(key).decrypt(ciphertext.encode("utf-8")).decode("utf-8")
