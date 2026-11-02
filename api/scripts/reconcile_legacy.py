"""Compare legacy Firestore with the platform database and list everything that did not arrive.

Read-only: it opens Firestore and Postgres for reading and commits nothing, so it is safe on
production. A row left out on purpose (deleted account, no email, merged into another product's
account) is listed as `expected`; everything else is a defect to repair.

    poetry run python scripts/reconcile_legacy.py                          # local database
    poetry run python scripts/reconcile_legacy.py --only users,attempts --csv misses.csv

    R="railway run -s platform-postgres -e staging poetry run python scripts/reconcile_legacy.py"
    $R --database-url-env RAILWAY_PROXY --csv staging-misses.csv
    (production: -s platform-postgres-production -e production)

Firestore credentials come from the same variables the importer reads
(GOOGLE_APPLICATION_CREDENTIALS, FIREBASE_SERVICE_ACCOUNT_KEY_PATH, ...).
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import sys
from typing import Any
from urllib.parse import urlparse

import regenerate_podcasts  # noqa: F401  # same folder; loads .env and the app
from railway_db import use_database_env  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.db import get_engine, import_all_models  # noqa: E402
from app.core.settings import get_settings  # noqa: E402
from app.migration import b2c_firestore, b2c_inventory, reconcile  # noqa: E402

ENTITIES = ("users", "stations", "attempts", "payments", "grants")


def _read(db: Any, step: str, collections: dict[str, str]) -> list[dict[str, Any]]:
    """Every non-seed document in the named collections of one import step."""
    documents: list[dict[str, Any]] = []
    for collection, exam in collections.items():
        found, _ = b2c_firestore.stream(db, collection, app_type=exam or None)
        print(f"  read {collection}: {len(found)}")  # noqa: T201
        documents.extend(found)
    return documents


async def _run(args: argparse.Namespace) -> int:
    if args.database_url_env:
        use_database_env(args.database_url_env)
    import_all_models()
    print(f"database host: {urlparse(get_settings().database_url).hostname or '?'}")  # noqa: T201
    chosen = set(args.only.split(",")) if args.only else set(ENTITIES)
    unknown = chosen - set(ENTITIES)
    if unknown:
        print(f"unknown entity: {sorted(unknown)}; choose from {ENTITIES}")  # noqa: T201
        return 2

    db = b2c_firestore.client()
    deleted = b2c_firestore.deleted_user_ids(db)
    findings: list[reconcile.Finding] = []
    engine = get_engine()
    async with AsyncSession(engine, expire_on_commit=False) as session:
        users = _read(db, "users", b2c_inventory.COPIED["users"]) if chosen & {"users", "grants"} else []
        if "users" in chosen:
            findings += await reconcile.reconcile_users(session, users, deleted)
        if "grants" in chosen:
            findings += await reconcile.reconcile_grants(session, users)
        if "stations" in chosen:
            stations = _read(db, "stations", b2c_inventory.COPIED["stations"])
            findings += await reconcile.reconcile_stations(session, stations)
        if "attempts" in chosen:
            transcripts = _read(
                db,
                "attempts",
                {name: exam for exam, name in b2c_inventory.TRANSCRIPT_COLLECTIONS.items()},
            )
            feedbacks = _read(
                db,
                "feedbacks",
                {name: exam for exam, name in b2c_inventory.FEEDBACK_COLLECTIONS.items()},
            )
            findings += await reconcile.reconcile_attempts(session, transcripts, deleted, feedbacks)
        if "payments" in chosen:
            payments = _read(db, "payments", b2c_inventory.COPIED["payments"])
            findings += await reconcile.reconcile_payments(session, payments)
        quality = await reconcile.data_quality_counts(session)
        await session.rollback()  # nothing was written; make that explicit
    await engine.dispose()

    print("\n--SUMMARY (reason: count; 'expected:' = left out on purpose)")  # noqa: T201
    for entity, counts in sorted(reconcile.summarise(findings).items()):
        print(f"{entity}: " + ", ".join(f"{reason}={n}" for reason, n in sorted(counts.items())))  # noqa: T201
    print("\n--DATA QUALITY")  # noqa: T201
    for name, value in quality.items():
        print(f"{name}: {value}")  # noqa: T201
    problems = reconcile.defects(findings)
    print(f"\nDEFECTS: {len(problems)} (expected exclusions: {len(findings) - len(problems)})")  # noqa: T201
    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["entity", "legacy_id", "collection", "reason", "expected", "detail"])
            for finding in findings:
                writer.writerow(
                    [
                        finding.entity,
                        finding.legacy_id,
                        finding.collection,
                        finding.reason,
                        finding.expected,
                        finding.detail,
                    ]
                )
        print(f"wrote {len(findings)} rows to {args.csv}")  # noqa: T201
    return 1 if problems else 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--database-url-env")
    parser.add_argument("--only", help=f"comma list from {ENTITIES}; default all")
    parser.add_argument("--csv", help="write every finding to this file")
    sys.exit(asyncio.run(_run(parser.parse_args())))


if __name__ == "__main__":
    main()
