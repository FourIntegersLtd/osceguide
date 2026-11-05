"""The password verifiers. `verify_legacy_password` reads the b2c bcrypt hashes
the migration carries into `users.legacy_password_hash`; it must never raise and
never accept an argon2 hash (nor `verify_password` a bcrypt one)."""

from __future__ import annotations

import asyncio
import time

import bcrypt
import pytest

from app.features.identity import tokens
from app.features.identity.tokens import (
    hash_password,
    verify_absent_password,
    verify_legacy_password,
    verify_password,
)

# Made by the retiring b2c backend's own flask-bcrypt 1.0.1 with its class
# defaults (prefix 2b, 12 rounds, no SHA-256 pre-hashing).
B2C_PASSWORD = "Legacy-Passw0rd!"
B2C_HASH = "$2b$12$7CnGAcydRjyhsnb2a3zOiOaeu/UrblrKtwwPDytxqMiVUgCJhGkC2"


async def test_a_real_b2c_hash_verifies_its_password() -> None:
    assert await verify_legacy_password(B2C_HASH, B2C_PASSWORD) is True


async def test_a_locally_made_bcrypt_hash_verifies() -> None:
    made = bcrypt.hashpw(b"another horse battery", bcrypt.gensalt(rounds=4)).decode()
    assert await verify_legacy_password(made, "another horse battery") is True


async def test_bcrypt_reads_only_the_first_72_bytes_as_b2c_did() -> None:
    long = "x" * 80
    made = bcrypt.hashpw(long.encode(), bcrypt.gensalt(rounds=4)).decode()
    assert await verify_legacy_password(made, "x" * 72 + "different tail") is True


@pytest.mark.parametrize("raw", ["wrong password here", "", B2C_PASSWORD.lower()])
async def test_a_wrong_password_is_not_a_match(raw: str) -> None:
    assert await verify_legacy_password(B2C_HASH, raw) is False


@pytest.mark.parametrize("stored", [None, "", "not a hash", B2C_HASH[:30], B2C_HASH + "x", "$2b$12$"])
async def test_a_missing_or_malformed_hash_is_false_not_an_error(stored: str | None) -> None:
    assert await verify_legacy_password(stored, B2C_PASSWORD) is False


async def test_the_two_verifiers_cannot_be_crossed() -> None:
    argon = await hash_password(B2C_PASSWORD)
    assert await verify_legacy_password(argon, B2C_PASSWORD) is False
    assert await verify_password(B2C_HASH, B2C_PASSWORD) is False
    assert await verify_password(argon, B2C_PASSWORD) is True


async def test_hashing_runs_off_the_event_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    """A concurrent task gets the loop while a slow hash is still running in its thread."""
    monkeypatch.setattr(tokens, "_hash_sync", lambda raw: (time.sleep(0.2), "hashed")[1])
    order: list[str] = []

    async def other() -> None:
        await asyncio.sleep(0)
        order.append("other")

    async def hashing() -> None:
        await hash_password("x")
        order.append("hash")

    await asyncio.gather(hashing(), other())
    assert order == ["other", "hash"]


async def test_every_verifier_leaves_the_loop_free() -> None:
    """Verify, legacy verify and the absent-user verify all run in a thread."""
    ticks = 0

    async def ticker() -> None:
        nonlocal ticks
        while True:
            await asyncio.sleep(0)
            ticks += 1

    task = asyncio.create_task(ticker())
    assert await verify_absent_password("whatever") is False
    assert await verify_legacy_password(B2C_HASH, B2C_PASSWORD) is True
    task.cancel()
    assert ticks > 1
