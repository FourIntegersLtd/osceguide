"""Fold every finished transcript's turn rows into one document, then give the disk back.

    DATABASE_URL=... python scripts/compact_transcripts.py                       # report only
    DATABASE_URL=... python scripts/compact_transcripts.py --yes                 # backfill
    DATABASE_URL=... python scripts/compact_transcripts.py --yes --vacuum        # + VACUUM
    DATABASE_URL=... python scripts/compact_transcripts.py --yes --vacuum --full # + VACUUM FULL

The periodic `compact_transcripts` task does the same work, but the worker has never run a
periodic task on production, so the one-off backfill is run by hand from here.

A dry run is the default: it prints sizes and counts and writes nothing. `--yes` is the only
thing that writes. The compaction itself is `service_compaction.compact_ready_transcripts`
(one transaction per attempt, newest delivered first, which is what lets a plain `VACUUM` hand the
tail of the table back to the OS).

Safe to stop (Ctrl-C) and re-run: each attempt is its own transaction and a compacted attempt is
skipped on the next pass. Attempts that fail to compact keep their rows, are named on stderr, and
make the script exit 1; the rest are done.

`DATABASE_URL` is required and no `.env` is loaded, so the script cannot quietly aim at a
database you did not name. VACUUM needs a direct or session-mode connection: on Supabase use the
session pooler on port 5432, not the transaction pooler on 6543. See docs/SUPPORT-RUNBOOK.md.

Delete this script, its test, the runbook section and the rule lines in staff-console.md in one
commit once the periodic `compact_transcripts` task is running on production.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TextIO
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("APP_ENV", "local")

import psycopg  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402

from app.core.db import import_all_models, libpq_url, sqlalchemy_url  # noqa: E402
from app.features.attempts import repository_transcript as transcripts  # noqa: E402
from app.features.attempts.service_compaction import (  # noqa: E402
    CompactionFailed,
    compact_ready_transcripts,
)
from app.features.health.repository_size import database_bytes  # noqa: E402

TRANSACTION_POOLER_PORT = 6543
BATCH_SIZE = 200  # attempts per pass; one transaction each
READ_ONLY_HINT = (
    "The database refused a write because it is read-only (an over-quota host does this).\n"
    "Free room first or raise the quota. If the host allows it, retry with\n"
    "  PGOPTIONS='-c default_transaction_read_only=off'\n"
    "in the environment, or run `SET default_transaction_read_only = off` on a psql session\n"
    "and use that connection. This script does not set it for you."
)


def read_only(error: BaseException | None) -> bool:
    """Whether this error, or anything it wraps, is the database refusing a write as read-only.

    The compaction wraps each attempt's error in `CompactionFailed` (cause), and SQLAlchemy wraps
    the driver's (`orig`), so both links are followed.
    """
    while error is not None:
        if isinstance(error, psycopg.errors.ReadOnlySqlTransaction):
            return True
        error = getattr(error, "orig", None) or error.__cause__
    return False


def say(*lines: object, file: TextIO | None = None) -> None:
    """The script's output; the one place a `print` is allowed."""
    print(*lines, file=file or sys.stdout, flush=True)  # noqa: T201


def mb(size_bytes: int) -> str:
    return f"{size_bytes / 1_000_000:,.1f} MB"


def describe(url: str) -> str:
    """host:port/database, never the credentials."""
    parts = urlsplit(url)
    return f"{parts.hostname}:{parts.port or 5432}{parts.path}"


def on_transaction_pooler(url: str) -> bool:
    return urlsplit(url).port == TRANSACTION_POOLER_PORT


def vacuum_refusal(url: str) -> str | None:
    """Why VACUUM cannot run on this connection, or None."""
    if on_transaction_pooler(url):
        return (
            f"{describe(url)} is the transaction-mode pooler (port {TRANSACTION_POOLER_PORT}), "
            "which rejects VACUUM.\nUse the session-mode pooler on port 5432 "
            "(same host and credentials) or a direct connection."
        )
    return None


@asynccontextmanager
async def _fresh_session(factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    async with factory() as session, session.begin():
        yield session


async def snapshot(factory: async_sessionmaker[AsyncSession]) -> dict[str, int]:
    """The numbers the operator decides on."""
    async with _fresh_session(factory) as session:
        row = (
            await session.execute(
                text(
                    "select pg_total_relation_size('transcript_messages'),"
                    " (select count(*) from transcript_messages),"
                    " (select count(*) from transcripts where message_count is not null),"
                    " (select count(*) from transcripts)"
                )
            )
        ).one()
        # Every transcript could be ready, so the count of them is a limit that cannot cut the list.
        ready = await transcripts.attempt_ids_ready_to_compact(session, limit=row[3])
        database = await database_bytes(session)
    return {"database": database, "table": row[0], "rows": row[1], "compacted": row[2], "ready": len(ready)}


def print_snapshot(label: str, state: dict[str, int]) -> None:
    say(f"{label}")
    say(f"  database size                 {mb(state['database'])}")
    say(f"  transcript_messages (total)   {mb(state['table'])}   (table + indexes + toast)")
    say(f"  transcript_messages rows      {state['rows']:,}")
    say(f"  attempts ready to compact     {state['ready']:,}")
    say(f"  attempts already compacted    {state['compacted']:,}")


async def backfill(factory: async_sessionmaker[AsyncSession]) -> tuple[int, list[str]]:
    """Compact batch by batch until nothing more can be. Answers (attempts compacted, failures).

    Progress is the growth of the compacted count, not the fall of the ready count: attempts
    cross the one-hour grace while a batch runs, so "ready" can rise while work is done, and
    `compact_ready_transcripts` raises away its own count when any attempt fails. A batch that
    raises `CompactionFailed` still compacted its other attempts, so the loop goes on while the
    compacted count grows. An attempt that keeps failing is the newest, so it is in every batch:
    it costs one slot, nothing more. The failures are returned for the caller to print and exit
    non-zero on. A read-only database fails every attempt alike, so that error is raised at once.
    """
    failures: list[str] = []
    batch = 0
    start = state = await snapshot(factory)
    while state["ready"]:
        batch += 1
        before = state["compacted"]
        try:
            await compact_ready_transcripts(lambda: _fresh_session(factory), limit=BATCH_SIZE)
        except CompactionFailed as failure:
            if read_only(failure):
                raise
            if str(failure) not in failures:  # the same poisoned attempts fail every batch: say it once
                say(f"batch {batch}: FAILED, {failure}", file=sys.stderr)
                failures.append(str(failure))
        state = await snapshot(factory)
        progress = state["compacted"] - before
        say(
            f"batch {batch}: {progress} compacted, "
            f"{state['ready']:,} remaining, database {mb(state['database'])}"
        )
        if not progress:
            say(
                f"No progress: {state['ready']:,} attempts remain and none compacted "
                "(they failed, or a writer raced each one). Stopping.",
                file=sys.stderr,
            )
            break
    return state["compacted"] - start["compacted"], failures


async def vacuum(url: str, factory: async_sessionmaker[AsyncSession], *, full: bool) -> None:
    """VACUUM, then optionally VACUUM FULL, on an autocommit connection outside any transaction."""
    notices: list[str] = []
    async with await psycopg.AsyncConnection.connect(libpq_url(url), autocommit=True) as conn:
        conn.add_notice_handler(lambda diag: notices.append(diag.message_primary or ""))
        await conn.execute("SET statement_timeout = 0")  # the host's default would cut a rewrite short
        statements = ["VACUUM (VERBOSE) transcript_messages"]
        if full:
            statements.append("VACUUM (FULL, VERBOSE) transcript_messages")
        for statement in statements:
            say(f"\n{statement} ...")
            notices.clear()
            await conn.execute(statement.encode())
            for line in notices:
                say(f"  {line}")
            state = await snapshot(factory)
            say(f"  after: database {mb(state['database'])}, transcript_messages {mb(state['table'])}")


async def main(args: argparse.Namespace, url: str) -> int:
    import_all_models()
    engine = create_async_engine(
        sqlalchemy_url(url),
        pool_size=1,
        pool_pre_ping=True,
        # A transaction pooler cannot keep a named prepared statement alive across calls.
        connect_args={"prepare_threshold": None},
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        say(f"Target: {describe(url)}\n")
        refusal = vacuum_refusal(url) if args.vacuum else None
        if refusal:  # before touching anything: a half-run that cannot finish is worse than none
            say(f"Refusing: {refusal}", file=sys.stderr)
            return 2
        before = await snapshot(factory)
        print_snapshot("Before", before)
        if not args.yes:
            plan = [f"compact {before['ready']:,} attempts in batches of {BATCH_SIZE}"]
            if args.vacuum:
                plan.append("VACUUM (VERBOSE) transcript_messages")
            if args.full:
                plan.append("VACUUM FULL transcript_messages (exclusive lock on the table while it runs)")
            say("\nDry run, nothing written. With --yes this would:")
            for step in plan:
                say(f"  - {step}")
            if not args.vacuum and on_transaction_pooler(url):
                say(f"\nNote: port {TRANSACTION_POOLER_PORT} cannot run VACUUM; use port 5432 for --vacuum.")
            return 0
        say(f"\nCompacting, {BATCH_SIZE} per batch (Ctrl-C is safe; re-run to continue)\n")
        done, failures = await backfill(factory)
        say(f"\nCompacted {done:,} attempts this run.")
        if failures:
            say(
                f"\nFAILED to compact: {failures[-1]}\n"
                "Their rows are untouched and still readable. Not vacuuming; fix the cause and re-run.",
                file=sys.stderr,
            )
            return 1
        if args.vacuum:
            await vacuum(url, factory, full=args.full)
        say()
        print_snapshot("After", await snapshot(factory))
        return 0
    except Exception as error:
        if read_only(error):
            say(f"\n{READ_ONLY_HINT}", file=sys.stderr)
            return 1
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--yes", action="store_true", help="write; without it nothing is changed")
    parser.add_argument("--vacuum", action="store_true", help="after compacting, VACUUM transcript_messages")
    parser.add_argument(
        "--full", action="store_true", help="with --vacuum, then VACUUM FULL (locks the table)"
    )
    parsed = parser.parse_args()
    if parsed.full and not parsed.vacuum:
        parser.error("--full needs --vacuum")
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        sys.exit("DATABASE_URL is not set. Name the database explicitly; no .env is read.")
    try:
        raise SystemExit(asyncio.run(main(parsed, database_url)))
    except KeyboardInterrupt:
        say(
            "\nInterrupted. The attempt in flight rolled back; every finished one stays compacted. "
            "Re-run to continue.",
            file=sys.stderr,
        )
        raise SystemExit(130) from None
