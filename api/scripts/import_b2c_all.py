"""One-way copy of every consumer Firestore collection into platform Postgres.

    poetry run python scripts/import_b2c_all.py --audit              # what is where; no database
    poetry run python scripts/import_b2c_all.py                      # dry run (default)
    poetry run python scripts/import_b2c_all.py --no-dry-run --skip-bad-records
    poetry run python scripts/import_b2c_all.py --only attempts,debriefs

**Firestore is only read** (`collections()` and `stream()`); nothing there is
written, updated or deleted. The collection list is `app/migration/b2c_inventory.py`,
and the run refuses to start if Firestore holds a collection it does not
account for, copied or skipped with a reason.

Steps run in dependency order in one transaction, each inside a savepoint:
users, stations, media, community, marketplace, attempts (transcripts and
feedback), live_coverage, debriefs, payments, referrals, partners, cvs,
site_messages, peer_practice. Every step is idempotent (deterministic ids or
natural keys), so re-running after Firestore has moved on copies only what is new.

A step that reports a problem is rolled back to its savepoint, like the
single-feature importers. `--skip-bad-records` keeps the step's good rows and
reports the bad ones instead: one orphaned comment should not hold back 90 good
ones. The exit status is non-zero whenever anything was reported.

`--dry-run` is the default: everything runs, then the transaction rolls back.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
os.environ.setdefault("APP_ENV", "local")

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_ROOT / ".env")
# The legacy b2c-api's .env sits beside api/ only in the old backend checkout;
# in the osceguide repository set the Firebase variables in the environment.
if (_ROOT.parent / "b2c-api" / ".env").is_file():
    load_dotenv(_ROOT.parent / "b2c-api" / ".env", override=False)

from sqlalchemy.exc import SQLAlchemyError  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.db import get_engine, import_all_models  # noqa: E402
from app.migration import b2c_firestore, b2c_inventory  # noqa: E402
from app.migration.b2c_steps import HANDLERS, STEPS, Run  # noqa: E402


def audit(db: object) -> list[str]:
    """Print every live collection with its count and fate; return the unaccounted ones."""
    names = b2c_firestore.root_collection_names(db)
    for name in names:
        count = db.collection(name).count().get()[0][0].value  # type: ignore[attr-defined]
        step = b2c_inventory.step_for(name)
        fate = f"copied by {step}" if step else f"skipped: {b2c_inventory.skip_reason(name) or 'UNACCOUNTED'}"
        print(f"  {name:<40} {count:>7}  {fate}")  # noqa: T201
    return b2c_inventory.unaccounted(names)


async def run(*, commit: bool, only: list[str], skip_bad: bool) -> int:
    db = b2c_firestore.client()
    missing = b2c_inventory.unaccounted(b2c_firestore.root_collection_names(db))
    if missing:
        raise SystemExit(
            f"Refusing to run: Firestore has collections the inventory does not cover: {missing}. "
            "Add each to app/migration/b2c_inventory.py, copied or skipped with a reason."
        )

    import_all_models()
    engine = get_engine()
    state = Run(db)
    reported = False
    async with AsyncSession(engine) as session:
        for step in [s for s in STEPS if not only or s in only]:
            print(f"== {step}")  # noqa: T201
            savepoint = await session.begin_nested()
            try:
                report = await HANDLERS[step](session, state)
            except SQLAlchemyError as exc:
                await savepoint.rollback()
                reported = True
                cause = str(getattr(exc, "orig", None) or exc).splitlines()[0][:300]
                print(f"   FAILED, step rolled back: {type(exc).__name__}: {cause}")  # noqa: T201
                continue
            print(f"   {report.summary()}")  # noqa: T201
            for problem in report.problems[:50]:
                print(f"   problem: {problem}")  # noqa: T201
            if len(report.problems) > 50:
                print(f"   ... and {len(report.problems) - 50} more problems")  # noqa: T201
            reported = reported or bool(report.problems)
            if report.problems and not skip_bad:
                await savepoint.rollback()
                print("   rolled this step back (pass --skip-bad-records to keep its good rows)")  # noqa: T201
            else:
                await savepoint.commit()
        if commit:
            await session.commit()
            print("committed")  # noqa: T201
        else:
            await session.rollback()
            print("rolled back: dry run (pass --no-dry-run to commit)")  # noqa: T201
    await engine.dispose()
    return 1 if reported else 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--audit", action="store_true", help="list every Firestore collection and its fate, then exit"
    )
    parser.add_argument(
        "--database-url-env",
        help="point at a Railway database, e.g. RAILWAY_PROXY under `railway run -s <postgres> -e <env>`",
    )
    parser.add_argument("--only", default="", help=f"comma-separated subset of: {', '.join(STEPS)}")
    parser.add_argument(
        "--skip-bad-records", action="store_true", help="keep a step's good rows when some fail"
    )
    parser.add_argument(
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="run everything and roll back (default). Pass --no-dry-run to commit.",
    )
    args = parser.parse_args()

    if args.database_url_env:
        from railway_db import use_database_env

        use_database_env(args.database_url_env)
    if args.audit:
        raise SystemExit(1 if audit(b2c_firestore.client()) else 0)
    only = [s.strip() for s in args.only.split(",") if s.strip()]
    unknown = sorted(set(only) - set(STEPS))
    if unknown:
        raise SystemExit(f"Unknown step(s) {unknown}; expected some of {STEPS}")
    raise SystemExit(asyncio.run(run(commit=not args.dry_run, only=only, skip_bad=args.skip_bad_records)))


if __name__ == "__main__":
    main()
