"""Give imported users who have not signed in on this app their legacy sign-up date as `activated_at`.

The free trial counts from `activated_at`, and the first sign-in sets it. Left empty, a lapsed legacy
subscriber gets a fresh trial on first sign-in. Only users with an empty `activated_at` and a
consumer identity link are touched; `created_at` already holds the legacy sign-up date.

    poetry run python scripts/fix_legacy_activated_at.py                       # local, dry run
    R="railway run -s platform-postgres -e staging poetry run python scripts/fix_legacy_activated_at.py"
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

AFFECTED = """from users where activated_at is null and exists (
  select 1 from user_identities i where i.user_id = users.id and i.provider = 'consumer')"""


async def _run(args: argparse.Namespace) -> int:
    if args.database_url_env:
        use_database_env(args.database_url_env)
    import_all_models()
    print(f"database host: {urlparse(get_settings().database_url).hostname or '?'}")  # noqa: T201
    async with get_engine().begin() as connection:
        count = await connection.scalar(text(f"select count(*) {AFFECTED}"))  # noqa: S608
        print(f"{count} imported users have no activated_at")  # noqa: T201
        if args.live:
            await connection.execute(
                text(f"update users set activated_at = created_at where id in (select id {AFFECTED})")  # noqa: S608
            )
            print("updated")  # noqa: T201
        else:
            print("dry run: nothing written, add --live to write")  # noqa: T201
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
