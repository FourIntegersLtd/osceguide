"""Hang every imported legacy attempt on the session station it was run from.

Run after the `mocks` and `attempts` import steps. Safe to repeat: only attempts still
`practice` are changed. Commits when it finishes.

    R="railway run -s platform-postgres-production -e production poetry run python"
    $R scripts/link_legacy_attempts_to_sessions.py --database-url-env RAILWAY_PROXY
"""

from __future__ import annotations

import argparse
import asyncio
from typing import Any

import regenerate_podcasts  # noqa: F401  # same folder; loads .env and the app
from railway_db import use_database_env  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.db import get_engine, import_all_models  # noqa: E402
from app.migration import b2c_firestore, b2c_inventory, b2c_lookups, load_b2c_mocks  # noqa: E402


def _read(db: Any, collections: dict[str, str]) -> list[dict[str, Any]]:
    """Every non-seed document in the named collections."""
    documents: list[dict[str, Any]] = []
    for collection, exam in collections.items():
        found, _ = b2c_firestore.stream(db, collection, app_type=exam or None)
        documents.extend(found)
    return documents


async def _run(args: argparse.Namespace) -> None:
    if args.database_url_env:
        use_database_env(args.database_url_env)
    import_all_models()
    db = b2c_firestore.client()
    mocks = _read(db, b2c_inventory.COPIED["mocks"])
    transcripts = _read(db, {name: exam for exam, name in b2c_inventory.TRANSCRIPT_COLLECTIONS.items()})
    engine = get_engine()
    async with AsyncSession(engine, expire_on_commit=False) as session:
        lookups = await b2c_lookups.build(session)
        report = await load_b2c_mocks.link_attempts_to_sessions(session, mocks, transcripts, lookups)
        await session.commit()
    await engine.dispose()
    print(report.counts)  # noqa: T201


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url-env")
    asyncio.run(_run(parser.parse_args()))


if __name__ == "__main__":
    main()
