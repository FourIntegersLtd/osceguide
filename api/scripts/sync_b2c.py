"""Bring the platform up to date with the old consumer site: only what is new or changed.

    poetry run python scripts/sync_b2c.py                    # preview: what is pending, nothing written
    poetry run python scripts/sync_b2c.py --no-dry-run       # copy it
    poetry run python scripts/sync_b2c.py --only attempts    # one step

Against staging or production, run it under that environment's Postgres service so Railway
supplies the connection (the secret is never printed or copied):

    railway run -s platform-postgres -e staging \
        poetry run python scripts/sync_b2c.py --database-url-env RAILWAY_PROXY --no-dry-run
    (production: -s platform-postgres-production -e production)

`scripts/sync_b2c_nightly.sh` wraps exactly that for the Mac's nightly schedule.

This is NOT a re-import. It lists every legacy document's id and last-changed time (no bodies),
subtracts what the ledger table `legacy_sync_records` says was already copied, fetches only the
rest, and records them afterwards. A document changed in Firestore since it was copied is fetched
again (that is how a user who has just bought a plan arrives); one that is unchanged is never
touched. A run on an empty ledger would offer every document to the add-only loaders (slow over the
Railway proxy), so the first run passes `--baseline-before <time of the last full import>`: older
documents are marked copied without being loaded, newer ones are copied normally.

Firestore is read only. Documents changed in the last 30 minutes wait for the next run.
Every step runs in one transaction, each inside a savepoint. A step that reports a problem keeps
its good rows and is reported once; a step that crashes is rolled back and records nothing, so its
documents are tried again next run. The exit status is non-zero whenever anything was reported.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
os.environ.setdefault("APP_ENV", "local")

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_ROOT / ".env")
if (_ROOT.parent / "b2c-api" / ".env").is_file():
    load_dotenv(_ROOT.parent / "b2c-api" / ".env", override=False)

from sqlalchemy.exc import SQLAlchemyError  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.db import get_engine, import_all_models  # noqa: E402
from app.migration import b2c_firestore, b2c_inventory, b2c_sync  # noqa: E402
from app.migration.b2c_steps import HANDLERS, STEPS, Run  # noqa: E402


def print_comparison(plans: list[b2c_sync.CollectionPlan]) -> None:
    """Firestore against the ledger, one line per collection that has anything in it."""
    print(f"{'collection':<40} {'in old site':>11} {'copied':>8} {'pending':>8} {'settling':>9}")  # noqa: T201
    for plan in plans:
        if plan.in_firestore:
            print(  # noqa: T201
                f"{plan.collection:<40} {plan.in_firestore:>11} {plan.already_copied:>8} "
                f"{plan.pending:>8} {plan.settling:>9}"
            )
    print(f"pending in total: {sum(plan.pending for plan in plans)}")  # noqa: T201


async def run(*, commit: bool, only: list[str], settle_minutes: int, cutoff: datetime | None) -> int:
    raw = b2c_firestore.client()
    missing = b2c_inventory.unaccounted(b2c_firestore.root_collection_names(raw))
    if missing:
        raise SystemExit(
            f"Refusing to run: Firestore has collections the inventory does not cover: {missing}. "
            "Add each to app/migration/b2c_inventory.py, copied or skipped with a reason."
        )

    import_all_models()
    engine = get_engine()
    reported = False
    async with AsyncSession(engine) as session:
        if not await b2c_sync.ledger_exists(session):
            if commit:
                raise SystemExit("legacy_sync_records is missing: run `alembic upgrade head` first")
            # A preview can run before the migration is deployed: the table is made inside the
            # transaction, and the rollback at the end removes it again.
            await b2c_sync.create_ledger(session)
            print("note: legacy_sync_records does not exist yet; previewing with an empty ledger")  # noqa: T201
        ledger = await b2c_sync.load_ledger(session)
        if cutoff is not None:
            covered = b2c_sync.baseline_rows(raw, ledger, cutoff)
            await b2c_sync.record(session, covered)
            ledger = await b2c_sync.load_ledger(session)
            print(f"baseline: {len(covered)} documents from before {cutoff:%Y-%m-%d %H:%M} marked as copied")  # noqa: T201
        print(f"ledger: {sum(len(ids) for ids in ledger.values())} documents already copied")  # noqa: T201
        pending, plans = b2c_sync.plan_pending(
            raw, ledger, now=b2c_sync.now_utc(), settle=timedelta(minutes=settle_minutes)
        )
        print_comparison(plans)
        wanted = b2c_sync.steps_with_work(plans)
        steps = [step for step in STEPS if step in wanted and (not only or step in only)]
        if not steps:
            print("nothing new to copy")  # noqa: T201
            await engine.dispose()
            return 0

        client = b2c_sync.PendingClient(raw, pending)
        b2c_firestore.use_client(client)
        state = Run(client, raw_db=raw)
        before = await b2c_sync.table_counts(session)
        for step in steps:
            print(f"== {step}")  # noqa: T201
            savepoint = await session.begin_nested()
            try:
                report = await HANDLERS[step](session, state)
            except SQLAlchemyError as exc:
                await savepoint.rollback()
                reported = True
                client.take_served(set(b2c_inventory.COPIED[step]))
                cause = str(getattr(exc, "orig", None) or exc).splitlines()[0][:300]
                print(f"   FAILED, step rolled back, will be retried: {type(exc).__name__}: {cause}")  # noqa: T201
                continue
            print(f"   {report.summary()}")  # noqa: T201
            for problem in report.problems[:50]:
                print(f"   problem: {problem}")  # noqa: T201
            if len(report.problems) > 50:
                print(f"   ... and {len(report.problems) - 50} more problems")  # noqa: T201
            await savepoint.commit()
            served = client.take_served(set(b2c_inventory.COPIED[step]))
            # A problem is a record the old site holds that cannot be copied as it stands (a user with
            # no email, a plan that no longer exists). It is reported once, here, and recorded like
            # the rest: asking again every night would never fix it. If staff edit the old record,
            # its new time makes it pending again.
            reported = reported or bool(report.problems)
            await b2c_sync.record(session, served)
            print(f"   {len(served)} documents recorded as copied")  # noqa: T201

        after = await b2c_sync.table_counts(session)
        print("== rows added")  # noqa: T201
        added = {table: after[table] - before[table] for table in after if after[table] != before[table]}
        for table, gained in sorted(added.items()):
            print(f"   {table:<40} {gained:+d}")  # noqa: T201
        if not added:
            print("   none")  # noqa: T201
        if commit:
            await session.commit()
            print("committed")  # noqa: T201
        else:
            await session.rollback()
            print("rolled back: preview only (pass --no-dry-run to copy)")  # noqa: T201
    await engine.dispose()
    return 1 if reported else 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--database-url-env",
        help="point at a Railway database, e.g. RAILWAY_PROXY under `railway run -s <postgres> -e <env>`",
    )
    parser.add_argument("--only", default="", help=f"comma-separated subset of: {', '.join(STEPS)}")
    parser.add_argument(
        "--settle-minutes",
        type=int,
        default=30,
        help="leave documents changed this recently for the next run (default 30)",
    )
    parser.add_argument(
        "--baseline-before",
        help=(
            "ISO time of the last full import (e.g. 2026-10-20T00:00:00+00:00). Documents last "
            "changed before it, and not yet in the ledger, are marked copied WITHOUT being loaded "
            "again. Use once, on the first run."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="show what would be copied and roll back (default). Pass --no-dry-run to copy.",
    )
    args = parser.parse_args()

    if args.database_url_env:
        from railway_db import use_database_env

        use_database_env(args.database_url_env)
    only = [step.strip() for step in args.only.split(",") if step.strip()]
    unknown = sorted(set(only) - set(STEPS))
    if unknown:
        raise SystemExit(f"Unknown step(s) {unknown}; expected some of {STEPS}")
    raise SystemExit(
        asyncio.run(
            run(
                commit=not args.dry_run,
                only=only,
                settle_minutes=args.settle_minutes,
                cutoff=datetime.fromisoformat(args.baseline_before) if args.baseline_before else None,
            )
        )
    )


if __name__ == "__main__":
    main()
