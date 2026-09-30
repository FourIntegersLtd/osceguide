"""Make the first platform admin of a database.

    python scripts/bootstrap_admin.py --email you@example.com --name "Your Name"
    make bootstrap-admin EMAIL=you@example.com

A fresh database has no exams, no rubrics and no station library — none of it
is seeded any more, and all of it is written through `/api/v1/platform/...` by
a platform admin. Which leaves one thing that cannot be done through the API:
making the first admin, because granting the right needs somebody who has it.

This is that one thing. Every admin after the first is made through the console:
`PUT /api/v1/platform/users/{id}/platform-admin`.

Promoting an existing account is the usual case and is safe to re-run. Creating
one sets `must_change_password`, so the password printed here is good for
exactly one login.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import secrets
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import get_session_factory, import_all_models  # noqa: E402
from app.core.secrets_at_rest import encrypt_text  # noqa: E402
from app.core.settings import get_settings  # noqa: E402
from app.features.identity import repository, repository_platform  # noqa: E402
from app.features.identity.service_passwords import hash_password  # noqa: E402


def admin_totp_secret() -> str:
    """The shared TOTP secret harnesses compute a code from, if one is configured."""
    configured = os.environ.get("ADMIN_TOTP_SECRET", "").strip()
    if configured:
        return configured
    for name in (".osce-staging-accounts.env", ".osce-local-accounts.env"):
        path = Path.home() / name
        if not path.is_file():
            continue
        for line in path.read_text().splitlines():
            stripped = line.strip()
            if stripped.startswith("ADMIN_TOTP_SECRET="):
                return stripped.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


async def ensure_admin_mfa(session: AsyncSession, user_id: UUID) -> None:
    """Confirm an authenticator from ADMIN_TOTP_SECRET when this admin has none yet.

    Re-running bootstrap does not replace an authenticator that is already
    confirmed: that secret is the one the person (and the harness) already has.
    """
    secret = admin_totp_secret()
    if not secret:
        print("No ADMIN_TOTP_SECRET. The next password sign-in must enrol an authenticator.")  # noqa: T201
        return
    existing = await repository.mfa_by_user(session, user_id)
    if existing is not None and existing.confirmed_at is not None:
        print("Authenticator already confirmed.")  # noqa: T201
        return
    now = datetime.now(UTC)
    await repository.save_pending_mfa_secret(
        session,
        user_id,
        secret_ciphertext=encrypt_text(secret, key=get_settings().mfa_secret_key),
        now=now,
    )
    await repository.confirm_mfa(session, user_id, at=now, step=0)
    print("Authenticator confirmed from ADMIN_TOTP_SECRET.")  # noqa: T201


async def bootstrap(*, email: str, name: str, password: str | None) -> int:
    import_all_models()
    factory = get_session_factory()
    async with factory() as session, session.begin():
        existing = await repository.user_by_email(session, email)
        if existing is not None:
            if existing.is_platform_admin:
                print(f"{email} is already a platform admin.")  # noqa: T201
            else:
                await repository_platform.set_platform_admin(session, existing.id, is_admin=True)
                print(f"{email} is now a platform admin.")  # noqa: T201
            await ensure_admin_mfa(session, existing.id)
            return 0

        generated = password or secrets.token_urlsafe(16)
        user = await repository.create_user(
            session,
            email=email,
            name=name,
            password_hash=hash_password(generated),
            is_platform_admin=True,
            must_change_password=True,
        )
        print(f"Created {email} ({user.id}) as a platform admin.")  # noqa: T201
        if password is None:
            print(f"One-time password: {generated}")  # noqa: T201
        print("It must be changed at first login.")  # noqa: T201
        await ensure_admin_mfa(session, user.id)
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", default="Platform Admin")
    parser.add_argument(
        "--password",
        default=None,
        help="Set a known password instead of generating one. It must still be changed at first login.",
    )
    args = parser.parse_args(argv)
    return asyncio.run(bootstrap(email=args.email, name=args.name, password=args.password))


if __name__ == "__main__":
    raise SystemExit(main())
