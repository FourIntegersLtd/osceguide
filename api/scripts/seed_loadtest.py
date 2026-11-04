"""Seed the accounts a k6 exam-burst run signs in as (`loadtest/README.md`).

    DATABASE_URL=... poetry run python scripts/seed_loadtest.py --count 50

Creates `trainee{i}@load-test.example.com` (i from 1), all sharing one password, each with a live grant on
the exam, and one published library station if the exam has none. Re-running adds only the
accounts that are missing and never hands out a second grant.

Refuses unless the database host is local or contains "staging": load accounts in production
would be real accounts nobody can reach.
"""

from __future__ import annotations

import argparse
import asyncio
import inspect
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.db import get_session_factory, import_all_models  # noqa: E402
from app.core.settings import get_settings  # noqa: E402
from app.features.catalog import service as catalog  # noqa: E402
from app.features.entitlements import service as entitlements  # noqa: E402
from app.features.identity import repository as identity  # noqa: E402
from app.features.identity.tokens import hash_password  # noqa: E402
from app.features.stations.models import Station, StationVersion  # noqa: E402

LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "host.docker.internal", ""})
DEFAULT_PASSWORD = "Load-test-password-1!"  # noqa: S105 - shared by throwaway load accounts only
EMAIL_DOMAIN = "load-test.example.com"  # not ".test": the email validator rejects special-use TLDs


def refuse_unless_safe(database_url: str) -> None:
    """Raise SystemExit unless the database is on this machine or a staging host."""
    host = (urlparse(database_url).hostname or "").lower()
    if host in LOCAL_HOSTS or "staging" in host:
        return
    raise SystemExit(f"Refusing to seed load accounts into host {host!r}: only local or *staging* hosts.")


def email_for(index: int) -> str:
    return f"trainee{index}@{EMAIL_DOMAIN}"


async def _hash_once(password: str) -> str:
    # `hash_password` may be sync or async; one hash is shared by every account.
    result = hash_password(password)
    return await result if inspect.isawaitable(result) else result


async def _ensure_station(session: AsyncSession, exam_code: str) -> str:
    exam = await catalog.resolve_exam(session, exam_code)
    existing = (
        await session.execute(
            select(StationVersion.id)
            .join(Station, Station.current_version_id == StationVersion.id)
            .where(Station.exam_id == exam.id, Station.status == "published", Station.approved.is_(True))
            .limit(1)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return f"existing station version {existing}"
    station = Station(
        owner_kind="platform",
        org_id=None,
        exam_id=exam.id,
        title="Load test station",
        status="published",
        approved=True,
    )
    session.add(station)
    await session.flush()
    version = StationVersion(
        station_id=station.id,
        org_id=None,
        version=1,
        content={"patient_information": {"persona": "anxious"}},
        status="published",
        published_at=datetime.now(UTC),
    )
    session.add(version)
    await session.flush()
    station.current_version_id = version.id
    return f"created station version {version.id}"


async def seed(*, count: int, exam_code: str, password: str) -> None:
    import_all_models()
    password_hash = await _hash_once(password)
    created = 0
    async with get_session_factory()() as session, session.begin():
        print(await _ensure_station(session, exam_code))  # noqa: T201
        for index in range(1, count + 1):
            email = email_for(index)
            if await identity.user_by_email(session, email) is not None:
                continue
            user = await identity.create_user(
                session,
                email=email,
                name=f"Load Trainee {index}",
                password_hash=password_hash,
                exam_code=exam_code,
                activated_at=datetime.now(UTC),
            )
            await entitlements.grant(
                session, user_id=user.id, exam_code=exam_code, source="admin", source_ref="seed_loadtest.py"
            )
            created += 1
    print(f"Created {created} of {count} accounts ({email_for(1)} .. {email_for(count)})")  # noqa: T201


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--exam", default="sca")
    parser.add_argument("--password", default=DEFAULT_PASSWORD)
    args = parser.parse_args()
    refuse_unless_safe(get_settings().database_url)
    asyncio.run(seed(count=args.count, exam_code=args.exam, password=args.password))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
