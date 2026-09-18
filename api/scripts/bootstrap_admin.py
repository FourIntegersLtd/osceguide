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
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import get_session_factory, import_all_models  # noqa: E402
from app.features.identity import repository  # noqa: E402
from app.features.identity.service_passwords import hash_password  # noqa: E402


async def bootstrap(*, email: str, name: str, password: str | None) -> int:
    import_all_models()
    factory = get_session_factory()
    async with factory() as session, session.begin():
        existing = await repository.user_by_email(session, email)
        if existing is not None:
            if existing.is_platform_admin:
                print(f"{email} is already a platform admin.")  # noqa: T201
                return 0
            await repository.set_platform_admin(session, existing.id, is_admin=True)
            print(f"{email} is now a platform admin.")  # noqa: T201
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
