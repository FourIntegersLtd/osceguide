"""Run the legacy import against a database.

    python scripts/migrate_legacy.py --export ./export --dry-run
    python scripts/migrate_legacy.py --export ./export
    python scripts/migrate_legacy.py --export ./export --verify-only

`--dry-run` is the default and has to be turned off deliberately. It is not a
separate code path: the import runs in full, against the real schema, and the
transaction is rolled back at the end. Every constraint the real run will hit
is hit by the dry run, and the report is the same report.

The export is a directory of JSON files, each an array of documents as
Firestore exports them:

    users.json            the four `*_users` collections, concatenated,
                          each document keeping its `app_type` and its `id`
    b2b_users.json        optional
    transcripts.json      the four `*_transcripts` collections
    feedbacks.json        optional, keyed by transcript id

Nothing about a failed run is kept. A record that cannot be loaded is reported
with the reason and the run continues, because one bad row should not abandon
the rest — but the exit status is non-zero if there was a single problem, so
this is safe to put in a pipeline.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("APP_ENV", "local")

from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.db import get_engine, import_all_models  # noqa: E402
from app.migration import loader, verify  # noqa: E402
from app.migration.attempts import attempt_from_transcript  # noqa: E402
from app.migration.users import UnknownLegacyProduct, entitlements_for, merge_users  # noqa: E402


def read(export: Path, name: str, *, required: bool = True) -> list[dict[str, Any]]:
    path = export / name
    if not path.exists():
        if required:
            raise SystemExit(f"{path} is missing.")
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit(f"{path} should hold a JSON array of documents.")
    return data


async def run(export: Path, *, commit: bool, verify_only: bool) -> int:
    users = read(export, "users.json")
    b2b = read(export, "b2b_users.json", required=False)
    transcripts = read(export, "transcripts.json", required=False)
    feedbacks = {str(f.get("transcript_id") or ""): f for f in read(export, "feedbacks.json", required=False)}

    merged = merge_users(users, b2b_users=b2b)
    grants = [g for record in users for g in entitlements_for(record)]

    try:
        migrated_attempts = [
            attempt_from_transcript(
                raw,
                app_type=str(raw.get("app_type") or ""),
                feedback=feedbacks.get(str(raw.get("transcript_id") or "")),
            )
            for raw in transcripts
        ]
    except UnknownLegacyProduct as exc:
        # Defaulting here is how CASC came to be marked with a GP rubric.
        raise SystemExit(f"Refusing to import: {exc}") from exc

    # Every mapped class, not just the ones this script names: SQLAlchemy
    # resolves foreign keys through the shared metadata, and a half-loaded
    # registry fails on `entitlements.org_id` before a single row is written.
    import_all_models()

    engine = get_engine()
    async with AsyncSession(engine) as session:
        if not verify_only:
            people, ids, _email_ids = await loader.load_users(session, merged, grants)
            attempts = await loader.load_attempts(session, migrated_attempts, user_ids=ids)
            report = people.merge(attempts)
            print(report.summary())  # noqa: T201
            for problem in report.problems:
                print(f"  problem: {problem}")  # noqa: T201
        else:
            report = loader.LoadReport()

        expected = verify.ExpectedCounts(
            users=len(merged),
            entitlements=len(grants),
            attempts=len(migrated_attempts),
            messages=sum(len(a.messages) for a in migrated_attempts),
            results=sum(1 for a in migrated_attempts if a.result is not None),
        )
        problems = await verify.compare_counts(session, expected)
        problems += await verify.spot_check(session, migrated_attempts[:50])
        if problems:
            for problem in problems:
                print(f"  verify: {problem}")  # noqa: T201
        else:
            print(  # noqa: T201
                f"verify: counts agree and {min(len(migrated_attempts), 50)} transcripts hash identically"
            )

        failed = bool(report.problems) or bool(problems)
        if commit and not failed:
            await session.commit()
            print("committed")  # noqa: T201
        else:
            await session.rollback()
            print("rolled back" if not commit else "rolled back: problems were reported")  # noqa: T201

    await engine.dispose()
    return 1 if failed else 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", type=Path, required=True, help="directory of JSON exports")
    parser.add_argument(
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="run everything and roll back (default). Pass --no-dry-run to commit.",
    )
    parser.add_argument("--verify-only", action="store_true", help="check a previous run without loading")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.export, commit=not args.dry_run, verify_only=args.verify_only)))


if __name__ == "__main__":
    main()
