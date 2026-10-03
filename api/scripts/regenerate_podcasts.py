"""Regenerate every podcast with ElevenLabs Eleven v4 (new script, new voices, new audio).

Covers `summary` rows (content.podcast_url), the `podcast` rows derived from them
(content.audio_url, pointed at the summary's new audio) and standalone `podcast`
rows that have a script or body_md. Each item is committed on its own, so a crash or
Ctrl-C loses nothing already done, and a re-run skips items already on the v4 audio.

    poetry run python scripts/regenerate_podcasts.py --dry-run
    poetry run python scripts/regenerate_podcasts.py --only <slug-substring> --limit 1
    poetry run python scripts/regenerate_podcasts.py --keep-scripts      # reuse stored scripts
    poetry run python scripts/regenerate_podcasts.py --force             # redo v4 items too

Staging or production: run it under Railway's Postgres service so no secret is copied, from api/:

    R="railway run -s platform-postgres -e staging poetry run python scripts/regenerate_podcasts.py"
    $R --database-url-env RAILWAY_PROXY --dry-run
    $R --database-url-env RAILWAY_PROXY --limit 1 --live

(production: -s platform-postgres-production -e production)
A database that is not on this machine is only written to with --live. Because every item is
committed on its own and already-v4 items are skipped, an interrupted run can simply be re-run.

Needs ELEVENLABS_API_KEY, OPENAI_API_KEY (or ANTHROPIC_API_KEY) and the AWS S3 settings.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote, urlparse

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
os.environ.setdefault("APP_ENV", "local")

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_ROOT / ".env")

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.db import get_engine, import_all_models  # noqa: E402
from app.core.settings import get_settings  # noqa: E402
from app.features.media.models import MediaItem  # noqa: E402
from app.features.media_production.podcast_tts import (  # noqa: E402
    produce_podcast_episode_audio,
    produce_summary_podcast,
)

V4_MARK = "/podcasts/v4/"


def _is_v4(url: object) -> bool:
    """Whether a stored audio URL already points at v4 audio."""
    return isinstance(url, str) and V4_MARK in url


def _railway_proxy_url() -> str:
    """The public connection string of a Railway Postgres service, from its own variables
    (so this must run under `railway run -s <postgres service> -e <environment>`)."""
    needed = (
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
        "RAILWAY_TCP_PROXY_DOMAIN",
        "RAILWAY_TCP_PROXY_PORT",
    )
    env = {key: os.environ.get(key, "").strip() for key in needed}
    missing = [key for key, value in env.items() if not value]
    if missing:
        sys.exit(
            f"missing {', '.join(missing)}; run under `railway run -s <postgres service> -e <environment>`"
        )
    return (
        f"postgresql://{quote(env['POSTGRES_USER'], safe='')}:{quote(env['POSTGRES_PASSWORD'], safe='')}"
        f"@{env['RAILWAY_TCP_PROXY_DOMAIN']}:{env['RAILWAY_TCP_PROXY_PORT']}/{env['POSTGRES_DB']}"
    )


def _use_database_env(name: str) -> None:
    """Points the app's DATABASE_URL at the connection string held in env var `name`,
    or at the Railway proxy address when `name` is RAILWAY_PROXY."""
    url = _railway_proxy_url() if name == "RAILWAY_PROXY" else (os.environ.get(name) or "").strip()
    if not url:
        sys.exit(f"{name} is not set")
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    os.environ["DATABASE_URL"] = url


async def _run(args: argparse.Namespace) -> int:
    if args.database_url_env:
        _use_database_env(args.database_url_env)
    import_all_models()
    settings = get_settings()
    host = urlparse(settings.database_url).hostname or "?"
    is_local = host in ("localhost", "127.0.0.1", "::1")
    print(f"database host: {host} ({'local' if is_local else 'REMOTE'})")  # noqa: T201
    if not is_local and not args.live and not args.dry_run:
        sys.exit("refusing to write to a remote database without --live (use --dry-run to look first)")
    engine = get_engine()
    failures = done = skipped = 0
    work = Path(tempfile.gettempdir()) / "regenerate_podcasts"
    regenerate_script = not args.keep_scripts

    async with AsyncSession(engine, expire_on_commit=False) as session:
        rows = (
            await session.scalars(
                select(MediaItem).where(MediaItem.kind.in_(("summary", "podcast"))).order_by(MediaItem.slug)
            )
        ).all()
        summaries = {row.slug: row for row in rows if row.kind == "summary"}
        todo: list[MediaItem] = []
        for row in rows:
            if args.only and args.only not in row.slug:
                continue
            if args.kind and row.kind != args.kind:
                continue
            if (
                row.kind == "summary"
                and not args.only
                and not (row.content.get("podcast_url") or row.content.get("audio_url"))
            ):
                continue  # this summary never had a podcast
            if row.kind == "podcast" and row.content.get("summary_slug") in summaries:
                continue  # follows its summary below
            if row.kind == "podcast" and not (row.content.get("script") or row.content.get("body_md")):
                print(f"skip   {row.slug}: standalone podcast with no script or body_md")  # noqa: T201
                skipped += 1
                continue
            key = "podcast_url" if row.kind == "summary" else "audio_url"
            if _is_v4(row.content.get(key)) and not args.force:
                skipped += 1
                continue
            todo.append(row)
        todo = todo[: args.limit] if args.limit else todo
        print(f"{len(todo)} to regenerate, {skipped} skipped")  # noqa: T201
        if args.dry_run:
            for row in todo:
                print(f"would  {row.kind:8} {row.slug}")  # noqa: T201
            await engine.dispose()
            return 0

        # Generation (script, speech, upload) runs in worker threads, several at a
        # time; the shared session is only touched under `commit_lock`.
        slots = asyncio.Semaphore(max(1, args.workers))
        commit_lock = asyncio.Lock()

        async def regenerate(row: MediaItem) -> None:
            nonlocal done, failures
            # Plain copies: a rollback expires every loaded row, and a worker
            # reading `row.slug` after another's failure would hit the database.
            media_id, kind, slug, title = str(row.id), row.kind, row.slug, row.title
            source = row.content
            label = f"{kind:8} {slug}"
            produce = produce_summary_podcast if kind == "summary" else produce_podcast_episode_audio
            async with slots:
                try:
                    content = await asyncio.to_thread(
                        produce,
                        settings,
                        title=title,
                        content=source,
                        work_dir=work / media_id,
                        media_id=media_id,
                        regenerate_script=regenerate_script,
                    )
                    async with commit_lock:
                        try:
                            row.content = content
                            for twin in rows:
                                if twin.kind == "podcast" and twin.content.get("summary_slug") == slug:
                                    twin.content = {
                                        **twin.content,
                                        "audio_url": content["podcast_url"],
                                        "script": content["script"],
                                    }
                            await session.commit()
                        except Exception:
                            await session.rollback()
                            raise
                    done += 1
                    print(f"done   {label}", flush=True)  # noqa: T201
                except Exception as error:  # noqa: BLE001 - report and carry on with the next item
                    failures += 1
                    print(f"FAILED {label}: {error}", flush=True)  # noqa: T201

        await asyncio.gather(*(regenerate(row) for row in todo))
    await engine.dispose()
    print(f"{done} regenerated, {failures} failed, {skipped} skipped")  # noqa: T201
    return 1 if failures else 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="list what would be regenerated, change nothing"
    )
    parser.add_argument("--only", help="only rows whose slug contains this text")
    parser.add_argument(
        "--database-url-env",
        help="env var holding the database URL, or RAILWAY_PROXY to build it from a Railway Postgres service",
    )
    parser.add_argument("--live", action="store_true", help="allow writing to a database that is not local")
    parser.add_argument("--kind", choices=("summary", "podcast"), help="only this kind of row")
    parser.add_argument("--limit", type=int, help="stop after this many items")
    parser.add_argument(
        "--keep-scripts", action="store_true", help="reuse stored scripts instead of rewriting"
    )
    parser.add_argument("--workers", type=int, default=1, help="episodes generated at the same time")
    parser.add_argument("--force", action="store_true", help="redo items already on v4 audio")
    sys.exit(asyncio.run(_run(parser.parse_args())))


if __name__ == "__main__":
    main()
