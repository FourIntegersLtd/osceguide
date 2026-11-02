"""Mark imported attempts that were never marked in the legacy app as "marking failed".

Such an attempt sits at `interaction_complete` with no result and no reason, so its feedback page
waits for a mark that is not coming. Setting `failed_reason = scoring_failed` makes the page say so
and leaves the transcript there for staff to mark on request. Only legacy-imported attempts are touched.

    poetry run python scripts/fix_legacy_stuck_attempts.py                       # local, dry run
    R="railway run -s platform-postgres -e staging poetry run python scripts/fix_legacy_stuck_attempts.py"
    $R --database-url-env RAILWAY_PROXY [--live]
    (production: -s platform-postgres-production -e production)
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from urllib.parse import urlparse

import regenerate_podcasts  # noqa: F401  # same folder; loads .env and the app
from railway_db import use_database_env  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.db import get_engine, import_all_models  # noqa: E402
from app.core.settings import get_settings  # noqa: E402

STUCK = """from attempts where legacy_ref is not null and status = 'interaction_complete'
  and failed_reason is null and not exists (
    select 1 from assessment_results r where r.attempt_id = attempts.id)"""


async def _run(args: argparse.Namespace) -> int:
    if args.database_url_env:
        use_database_env(args.database_url_env)
    import_all_models()
    print(f"database host: {urlparse(get_settings().database_url).hostname or '?'}")  # noqa: T201
    async with get_engine().begin() as connection:
        count = await connection.scalar(text(f"select count(*) {STUCK}"))  # noqa: S608
        print(f"{count} imported attempts are stuck waiting for a mark")  # noqa: T201
        if args.live:
            await connection.execute(
                text(
                    f"update attempts set failed_reason = 'scoring_failed' where id in (select id {STUCK})"  # noqa: S608
                )
            )
            print("updated")  # noqa: T201
        else:
            print("dry run: nothing written, add --live to write")  # noqa: T201
    await get_engine().dispose()
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--database-url-env")
    parser.add_argument("--live", action="store_true", help="write; default is a dry run")
    sys.exit(asyncio.run(_run(parser.parse_args())))


if __name__ == "__main__":
    main()
