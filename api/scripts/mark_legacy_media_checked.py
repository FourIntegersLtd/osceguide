"""Tick the fact check and the script check on published study media imported from the legacy
tool. Those items were checked by hand before the app kept check records, so their steps read
"Not recorded". This stores a by-hand check (no claims) for what is missing and never replaces a
check already on record. Only published, voiced decks, summaries and podcasts are touched.

    poetry run python scripts/mark_legacy_media_checked.py                 # local, dry run
    poetry run python scripts/mark_legacy_media_checked.py --live          # local, writes

    R="railway run -s platform-postgres -e staging poetry run python scripts/mark_legacy_media_checked.py"
    $R --database-url-env RAILWAY_PROXY                                    # dry run: counts
    $R --database-url-env RAILWAY_PROXY --live                             # writes
    (production: -s platform-postgres-production -e production)
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import regenerate_podcasts  # noqa: F401  # same folder; loads .env and the app
from railway_db import use_database_env  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402
from sqlalchemy.orm.attributes import flag_modified  # noqa: E402

from app.core.db import get_engine, import_all_models  # noqa: E402
from app.core.settings import get_settings  # noqa: E402
from app.features.media.models import MediaItem  # noqa: E402
from app.features.media_production import script_check, service_facts  # noqa: E402

CHECKED_BY = "Manual review before automated checks"
VOICED_FIELD = {"slide_deck": "final_video_url", "summary": "podcast_url", "podcast": "audio_url"}


def fill_missing_checks(row: MediaItem) -> dict[str, bool]:
    """Adds the missing checks to a row's content; returns which of `facts` and `script` it added."""
    content: dict[str, Any] = dict(row.content or {})
    review = dict(content.get("review") or {})
    added = {"facts": False, "script": False}
    if not review.get("facts"):
        sections = service_facts.sections_of(row.kind, row.title, content)
        review["facts"] = {
            "checked_at": datetime.now(UTC).isoformat(),
            "source_hash": service_facts.fingerprint(sections),
            "claims": [],
            "checked_by": CHECKED_BY,
        }
        added["facts"] = True
    content["review"] = review
    if not review.get("script") and script_check.spoken_lines(row.kind, content):
        script_check.mark_checked(row.kind, row.title, content)
        added["script"] = True
    if any(added.values()):
        row.content = content
        flag_modified(row, "content")
    return added


async def _run(args: argparse.Namespace) -> int:
    if args.database_url_env:
        use_database_env(args.database_url_env)
    import_all_models()
    host = urlparse(get_settings().database_url).hostname or "?"
    is_local = host in ("localhost", "127.0.0.1", "::1")
    print(f"database host: {host} ({'local' if is_local else 'REMOTE'})")  # noqa: T201
    engine = get_engine()
    async with AsyncSession(engine, expire_on_commit=False) as session:
        rows = (
            await session.scalars(
                select(MediaItem).where(MediaItem.status == "published", MediaItem.kind.in_(VOICED_FIELD))
            )
        ).all()
        facts = script = skipped_unvoiced = skipped_no_lines = 0
        for row in rows:
            content = row.content or {}
            if not str(content.get(VOICED_FIELD[row.kind]) or "").strip():
                skipped_unvoiced += 1
                continue
            added = fill_missing_checks(row)
            facts += added["facts"]
            script += added["script"]
            if not (content.get("review") or {}).get("script") and not added["script"]:
                skipped_no_lines += 1
        print(  # noqa: T201
            f"{len(rows)} published: {facts} facts ticked, {script} scripts ticked, "
            f"{skipped_unvoiced} not voiced (skipped), "
            f"{skipped_no_lines} with no spoken lines (script skipped)"
        )
        if args.live:
            await session.commit()
            print("committed")  # noqa: T201
        else:
            await session.rollback()
            print("dry run: nothing written")  # noqa: T201
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
