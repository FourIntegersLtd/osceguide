"""Copy already-generated v4 podcast audio URLs and narrated slide decks from one database to
another, without generating anything. Rows are matched by (kind, slug), so the target must hold
the same summaries, podcasts and slide decks as the source.

    R="railway run -s platform-postgres -e staging poetry run python scripts/copy_podcast_urls.py"
    $R export urls.json --database-url-env RAILWAY_PROXY

    R="railway run -s platform-postgres-production -e production"
    R="$R poetry run python scripts/copy_podcast_urls.py"
    $R apply urls.json --database-url-env RAILWAY_PROXY            # dry run: reports matches
    $R apply urls.json --database-url-env RAILWAY_PROXY --live     # writes

Only content.podcast_url (summaries) or content.audio_url (podcasts), plus content.script, change.
A slide deck narrated in Ben's voice is copied whole: its video, narration, speaker notes and pictures.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

import regenerate_podcasts as rp  # same folder; loads .env and the app
from regenerate_slides import NARRATION_MARK  # noqa: E402  # same folder
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.db import get_engine, import_all_models  # noqa: E402
from app.core.settings import get_settings  # noqa: E402
from app.features.media.models import MediaItem  # noqa: E402

URL_KEY = {"summary": "podcast_url", "podcast": "audio_url"}
SLIDE_DECK = "slide_deck"


async def _run(args: argparse.Namespace) -> int:
    if args.database_url_env:
        rp._use_database_env(args.database_url_env)
    import_all_models()
    host = urlparse(get_settings().database_url).hostname or "?"
    is_local = host in ("localhost", "127.0.0.1", "::1")
    print(f"database host: {host} ({'local' if is_local else 'REMOTE'})")  # noqa: T201
    engine = get_engine()
    async with AsyncSession(engine, expire_on_commit=False) as session:
        rows = (
            await session.scalars(select(MediaItem).where(MediaItem.kind.in_((*URL_KEY, SLIDE_DECK))))
        ).all()
        if args.command == "export":
            items = [
                {
                    "kind": r.kind,
                    "slug": r.slug,
                    "url": r.content[URL_KEY[r.kind]],
                    "script": r.content.get("script"),
                }
                for r in rows
                if r.kind in URL_KEY and rp.V4_MARK in str(r.content.get(URL_KEY[r.kind]) or "")
            ] + [
                {"kind": r.kind, "slug": r.slug, "content": r.content}
                for r in rows
                if r.kind == SLIDE_DECK and r.content.get("narration_voice") == NARRATION_MARK
            ]
            Path(args.file).write_text(json.dumps(items, indent=1))
            print(f"exported {len(items)} podcast urls and narrated slide decks to {args.file}")  # noqa: T201
        else:
            if not is_local and not args.live and not args.dry_run:
                sys.exit("refusing to write to a remote database without --live")
            by_key = {(r.kind, r.slug): r for r in rows}
            items = json.loads(Path(args.file).read_text())
            matched = [(by_key[(i["kind"], i["slug"])], i) for i in items if (i["kind"], i["slug"]) in by_key]
            print(f"{len(matched)} of {len(items)} match a row here")  # noqa: T201
            if args.live:
                for row, item in matched:
                    if row.kind == SLIDE_DECK:
                        row.content = item["content"]
                        continue
                    update = {URL_KEY[row.kind]: item["url"]}
                    if item.get("script"):
                        update["script"] = item["script"]
                    row.content = {**row.content, **update}
                await session.commit()
                print("committed")  # noqa: T201
    await engine.dispose()
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("command", choices=("export", "apply"))
    parser.add_argument("file")
    parser.add_argument("--database-url-env")
    parser.add_argument("--live", action="store_true", help="write (apply only); default is a dry run")
    args = parser.parse_args()
    args.dry_run = not args.live
    sys.exit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
