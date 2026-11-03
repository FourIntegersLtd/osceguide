"""Point database rows at the platform bucket.

The platform keeps its files in a bucket of its own, as `<kind>/<exam>/...` (`app/core/bucket_layout.py`).
The legacy site's links name the old bucket and its old places (`yahayakenny/`, `fourint/`,
`Four Integers Ltd/`, `teaching_videos/v2/`, `podcasts/v4/`, `human_practice/`, ...).
`app/migration/bucket_moves.py` says where each one went; the legacy importers use the same rules. Every
text or JSON column that holds an old-bucket link is rewritten here, and so is the one column that stores a
bare key (`practice_sessions.recording_key`). A link keeps the spelling its path had (plain, `%20`, `+` or
fully encoded); its host becomes the platform bucket's.
Copy the files first: `scripts/copy_to_platform_bucket.py`.

    # dry run: lists each column that holds an old link and how many rows
    railway run -s platform-postgres-production -e production \
        poetry run python scripts/move_bucket_links.py --database-url-env RAILWAY_PROXY
    # then the same command with --live to write

Run it against staging first. The old files stay in the old bucket until the old site that still reads them
is retired, so running this twice, or late, is harmless. The report at the end must list nothing before the
old bucket is deleted.
"""

from __future__ import annotations

import argparse
import asyncio
import collections
import re
import sys
from urllib.parse import unquote_plus, urlparse

from railway_db import bootstrap_app, use_database_env

bootstrap_app()

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncConnection  # noqa: E402

from app.core.db import get_engine, import_all_models  # noqa: E402
from app.core.settings import get_settings  # noqa: E402
from app.migration.bucket_moves import LEGACY_HOST, platform_key, rewrite_links  # noqa: E402

LINK = re.compile(LEGACY_HOST + r"/(?P<key>[^\"'\s?)\\]+)", re.IGNORECASE)
JSON_TYPES = ("json", "jsonb")
TEXT_TYPES = ("text", "character varying")


def folder_of(key: str) -> str:
    """The top-level folder a bucket key sits in, for the report of links that did not move."""
    parts = key.split("/")
    return parts[0] if len(parts) > 1 else "(bucket root)"


async def rewrite_recording_keys(connection: AsyncConnection, *, live: bool) -> int:
    """Move `practice_sessions.recording_key` (a bare key, not a link) to its place in the platform bucket."""
    found = await connection.execute(
        text("select ctid::text, recording_key from practice_sessions where recording_key is not null")
    )
    changed = [
        (str(row[0]), moved) for row in found if (moved := platform_key(str(row[1]))) and moved != row[1]
    ]
    if changed:
        print(f"practice_sessions.recording_key: {len(changed)} row(s)")  # noqa: T201
    if live:
        for row_id, moved in changed:
            await connection.execute(
                text("update practice_sessions set recording_key = :value where ctid = cast(:row_id as tid)"),
                {"value": moved, "row_id": row_id},
            )
    return len(changed)


async def link_columns(connection: AsyncConnection) -> list[tuple[str, str, str]]:
    """Every (table, column, type) in the public schema that can hold a link: JSON and text columns."""
    rows = await connection.execute(
        text(
            "select table_name, column_name, data_type from information_schema.columns "
            "where table_schema = 'public' and data_type = any(:types) order by 1, 2"
        ),
        {"types": [*JSON_TYPES, *TEXT_TYPES]},
    )
    return [(str(row[0]), str(row[1]), str(row[2])) for row in rows]


async def _run(live: bool) -> int:
    import_all_models()
    host = urlparse(get_settings().database_url).hostname or "?"
    print(f"database host: {host} ({'local' if host in ('localhost', '127.0.0.1', '::1') else 'REMOTE'})")  # noqa: T201
    total = 0
    remaining: collections.Counter[str] = collections.Counter()
    left_keys: set[str] = set()
    async with get_engine().begin() as connection:
        for table, column, data_type in await link_columns(connection):
            # Names come from information_schema, never from input. Only rows that name our bucket are read.
            found = await connection.execute(
                text(
                    f'select ctid::text, "{column}"::text from "{table}" '  # noqa: S608
                    f"where \"{column}\"::text like '%osceguide%amazonaws.com%'"
                )
            )
            rows = [(str(row[0]), str(row[1])) for row in found]
            for _row_id, original in rows:
                for match in LINK.finditer(rewrite_links(original)):
                    remaining[folder_of(unquote_plus(match["key"]))] += 1
                    left_keys.add(unquote_plus(match["key"]))
            changed = [
                (row_id, rewritten)
                for row_id, original in rows
                if (rewritten := rewrite_links(original)) != original
            ]
            if not changed:
                continue
            total += len(changed)
            print(f"{table}.{column}: {len(changed)} row(s)")  # noqa: T201
            if live:
                cast = f"cast(:value as {data_type})" if data_type in JSON_TYPES else ":value"
                for row_id, rewritten in changed:
                    await connection.execute(
                        text(f'update "{table}" set "{column}" = {cast} where ctid = cast(:row_id as tid)'),  # noqa: S608
                        {"value": rewritten, "row_id": row_id},
                    )
        total += await rewrite_recording_keys(connection, live=live)
    print(f"{'rewrote' if live else 'would rewrite'} {total} row(s)")  # noqa: T201
    print("links still on the old bucket, by folder (each one did not move; none should be left):")  # noqa: T201
    for folder, count in sorted(remaining.items()):
        print(f"  {folder}: {count}")  # noqa: T201
    for key in sorted(left_keys)[:60]:
        print(f"    left: {key}")  # noqa: T201
    return 0


def main() -> int:
    """Parse the flags and run."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--database-url-env", help="env var holding the database to use (see railway_db)")
    parser.add_argument("--live", action="store_true", help="write the changes (default: dry run)")
    args = parser.parse_args()
    if args.database_url_env:
        use_database_env(args.database_url_env)
    return asyncio.run(_run(args.live))


if __name__ == "__main__":
    sys.exit(main())
