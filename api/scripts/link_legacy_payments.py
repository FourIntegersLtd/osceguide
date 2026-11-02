"""Tie imported payments to the access they bought, and fill a missing plan.

Without the link a legacy subscriber has no station limit, can buy the same plan twice, and a refund
does not remove their access. Dry run by default: it lists what it would link and every payment it
cannot place (needs a human). Nothing is guessed.

    poetry run python scripts/link_legacy_payments.py                  # local, dry run
    R="railway run -s platform-postgres -e staging poetry run python scripts/link_legacy_payments.py"
    $R --database-url-env RAILWAY_PROXY                                # dry run: counts
    $R --database-url-env RAILWAY_PROXY --live                         # writes
    (production: -s platform-postgres-production -e production)
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from urllib.parse import urlparse

import regenerate_podcasts  # noqa: F401  # same folder; loads .env and the app
from railway_db import use_database_env  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.db import get_engine, import_all_models  # noqa: E402
from app.core.settings import get_settings  # noqa: E402
from app.migration.link_payments import link_legacy_payments  # noqa: E402


async def _run(args: argparse.Namespace) -> int:
    if args.database_url_env:
        use_database_env(args.database_url_env)
    import_all_models()
    print(f"database host: {urlparse(get_settings().database_url).hostname or '?'}")  # noqa: T201
    engine = get_engine()
    async with AsyncSession(engine, expire_on_commit=False) as session:
        report = await link_legacy_payments(session)
        summary = f"linked {report.linked}, plans filled {report.plans_filled}, "
        print(summary + f"needs a human {len(report.unresolved)}")  # noqa: T201
        for line in report.unresolved:
            print(f"  {line}")  # noqa: T201
        if args.live:
            await session.commit()
            print("committed")  # noqa: T201
        else:
            await session.rollback()
            print("dry run: nothing written, add --live to write")  # noqa: T201
    await engine.dispose()
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
