"""Fill two fields on slide decks that were made before they existed: content.topic (the deck's
subject, shown as its heading) and content.captions_vtt (the caption track, cut from the timings
the render stored). A deck that already has a field keeps it; a deck with no timings gets no
captions. Staff run this by hand; nothing in the app calls it.

    poetry run python scripts/sync_deck_topics_and_captions.py             # local, dry run
    poetry run python scripts/sync_deck_topics_and_captions.py --live      # local, writes

    R="railway run -s platform-postgres -e staging poetry run python scripts/sync_deck_topics_and_captions.py"
    $R --database-url-env RAILWAY_PROXY                                    # dry run: counts
    $R --database-url-env RAILWAY_PROXY --live                             # writes
    (production: -s platform-postgres-production -e production)
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from typing import Any
from urllib.parse import urlparse

import regenerate_podcasts  # noqa: F401  # same folder; loads .env and the app
from railway_db import use_database_env  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.db import get_engine, import_all_models  # noqa: E402
from app.core.settings import get_settings  # noqa: E402
from app.features.media.models import MediaItem  # noqa: E402
from app.features.media_production.captions import deck_captions_vtt  # noqa: E402

PLACEHOLDER = re.compile(r"^(slide\s*\d*|untitled.*|new deck.*)?$", re.IGNORECASE)


def topic_for(title: str, content: dict[str, Any]) -> str | None:
    """The deck's subject: its title, or its first slide's title when the title is a placeholder."""
    if not PLACEHOLDER.match(title.strip()):
        return title.strip()
    for slide in content.get("slides") or []:
        first = str(slide.get("title") or "").strip() if isinstance(slide, dict) else ""
        if first and not PLACEHOLDER.match(first):
            return first
    return None


def changes_for(row: MediaItem) -> dict[str, str]:
    content = dict(row.content or {})
    found: dict[str, str] = {}
    if not str(content.get("topic") or "").strip() and (topic := topic_for(row.title, content)):
        found["topic"] = topic
    if not content.get("captions_vtt") and (captions := deck_captions_vtt(content)):
        found["captions_vtt"] = captions
    return found


async def _run(args: argparse.Namespace) -> int:
    if args.database_url_env:
        use_database_env(args.database_url_env)
    import_all_models()
    host = urlparse(get_settings().database_url).hostname or "?"
    is_local = host in ("localhost", "127.0.0.1", "::1")
    print(f"database host: {host} ({'local' if is_local else 'REMOTE'})")  # noqa: T201
    if not is_local and not args.live:
        print("remote database: dry run only, add --live to write")  # noqa: T201
    engine = get_engine()
    async with AsyncSession(engine, expire_on_commit=False) as session:
        rows = (await session.scalars(select(MediaItem).where(MediaItem.kind == "slide_deck"))).all()
        topics = captions = 0
        for row in rows:
            found = changes_for(row)
            topics += "topic" in found
            captions += "captions_vtt" in found
            if found and args.live:
                row.content = {**row.content, **found}
        print(f"{len(rows)} decks: {topics} need a topic, {captions} can have captions")  # noqa: T201
        if args.live:
            await session.commit()
            print("committed")  # noqa: T201
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
