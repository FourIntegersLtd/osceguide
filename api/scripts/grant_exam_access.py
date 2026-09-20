"""Grant a user live access to an exam (local dev / support).

Study material bodies require a live entitlement — OpenAI does not substitute
for that. After seeding media, run:

    poetry run python scripts/grant_exam_access.py --email you@example.com --exam sca

Or: make grant-exam-access EMAIL=you@example.com EXAM=sca
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import get_session_factory, import_all_models  # noqa: E402
from app.features.entitlements import service as entitlements  # noqa: E402
from app.features.identity import repository as identity  # noqa: E402


async def main(*, email: str, exam_code: str, days: int) -> int:
    import_all_models()
    factory = get_session_factory()
    now = datetime.now(tz=UTC)
    async with factory() as session, session.begin():
        user = await identity.user_by_email(session, email)
        if user is None:
            print(f"No user with email {email}")  # noqa: T201
            return 1
        ends_at = now + timedelta(days=days) if days > 0 else None
        row = await entitlements.grant(
            session,
            user_id=user.id,
            exam_code=exam_code,
            source="admin",
            source_ref="grant_exam_access.py",
            ends_at=ends_at,
            granted_by=None,
        )
        print(  # noqa: T201
            f"Granted {exam_code.upper()} to {email} (entitlement {row.id}, live={row.live})"
        )
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--exam", default="sca", help="exam code, e.g. sca, plab")
    parser.add_argument("--days", type=int, default=365, help="0 = no expiry")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(email=args.email, exam_code=args.exam, days=args.days)))
