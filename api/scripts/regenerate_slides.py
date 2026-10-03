"""Re-render slide decks as narrated mp4s, with Ben's ElevenLabs voice.

Each slide is narrated as an intro plus one line per bullet (written by the model from the
deck's own notes), and a bullet appears exactly when its line starts, so speech and slide cannot
drift. Rendering raises rather than skipping a line, and S3 upload failures are errors.

    # one deck, rendered on this machine: no upload, no database write
    poetry run python scripts/regenerate_slides.py --sample <slug-substring>              # first 4 slides
    poetry run python scripts/regenerate_slides.py --sample <slug-substring> --slides 0   # the whole deck

A sample keeps its narration and Ben's recordings beside the video, so rendering it again after
a change to the look costs nothing; --force writes and voices it afresh.

    # staging (run under Railway's Postgres service, like regenerate_podcasts.py)
    R="railway run -s platform-postgres -e staging poetry run python scripts/regenerate_slides.py"
    $R --database-url-env RAILWAY_PROXY --dry-run
    $R --database-url-env RAILWAY_PROXY --limit 1 --live
    $R --database-url-env RAILWAY_PROXY --live

    # put a sample that was approved as it is on a database, without rendering it again
    $R --database-url-env RAILWAY_PROXY --live --publish-sample <slug-substring> --sample-file <sample.json>

Every deck is committed on its own and decks already on this narration are skipped, so an
interrupted run can simply be re-run. Needs ELEVENLABS_API_KEY, OPENAI_API_KEY (or
ANTHROPIC_API_KEY) and the AWS S3 settings.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import regenerate_podcasts as rp  # noqa: E402  (sets up the path, env and .env loading)
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.db import get_engine, import_all_models  # noqa: E402
from app.core.settings import get_settings  # noqa: E402
from app.features.media.models import MediaItem  # noqa: E402
from app.features.media_production.slide_av import regenerate_slide_av, upload_video  # noqa: E402
from app.features.media_production.slide_narration import spoken_notes  # noqa: E402

NARRATION_MARK = "elevenlabs-ben-v1"


def _print_timeline(content: dict[str, Any]) -> None:
    """Each slide's intro and bullet start times, to check by eye against the video."""
    lines: list[str] = []
    for slide in content.get("slides", []):
        lines.append(
            f"slide {slide.get('position')}: {slide.get('title')} at {slide.get('start_time', 0):.1f}s "
            f"({slide.get('audio_duration', 0):.1f}s)"
        )
        if slide.get("intro_duration"):
            lines.append(f"    0.0s  intro   {slide['narration']['intro'][:70]}")
        for segment in slide.get("bullet_audio_segments") or []:
            number = segment["bullet_index"] + 1
            lines.append(f"  {segment['start_time']:5.1f}s  item {number}  {segment['text'][:70]}")
    plan = content.get("presentation") or {}
    for section in plan.get("sections", []):
        lines.append(f"card before slide {section['before']}: {section['title']} | {section['line']}")
    for takeaway in plan.get("takeaways", []):
        lines.append(f"takeaway: {takeaway['text']} | {takeaway['line']}")
    lines.append(f"sign-off: {plan.get('signoff')}")
    print("\n".join(lines))  # noqa: T201


def _reuse_sample_narration(source: dict[str, Any], kept: Path) -> None:
    """Puts the words of the last sample render of this deck back on it, so they are not rewritten."""
    if not kept.exists():
        return
    previous = json.loads(kept.read_text(encoding="utf-8"))
    narrated = {slide.get("id"): slide.get("narration") for slide in previous.get("slides", [])}
    source["slides"] = [{**slide, "narration": narrated.get(slide.get("id"))} for slide in source["slides"]]
    if len(previous.get("slides", [])) == len(source["slides"]):
        source["presentation"] = previous.get("presentation")


async def _store(engine: Any, media_id: Any, content: dict[str, Any]) -> None:
    """Saves a rendered deck on its row over a connection opened now: the one the decks were read
    on has sat idle through a render and may be gone."""
    stored = {key: value for key, value in content.items() if key != "local_video_path"}
    async with AsyncSession(engine) as session:
        row = await session.get(MediaItem, media_id)
        if row is None:
            raise LookupError(f"deck {media_id} is no longer in the database")
        row.content = {**stored, "narration_voice": NARRATION_MARK}
        await session.commit()


def _approved_sample(row: MediaItem, sample_file: str) -> dict[str, Any]:
    """The content of a sample render, checked to be of this deck, with its speaker notes set to
    what Ben says in it."""
    content: dict[str, Any] = json.loads(Path(sample_file).read_text(encoding="utf-8"))
    titles = [slide.get("title") for slide in content.get("slides", [])]
    if titles != [slide.get("title") for slide in row.content.get("slides", [])]:
        raise ValueError(f"{sample_file} is not a full render of {row.slug}")
    for slide in content["slides"]:
        slide.setdefault("source_notes", slide.get("speaker_notes", ""))
        slide["speaker_notes"] = spoken_notes(slide["narration"])
    return content


async def _run(args: argparse.Namespace) -> int:
    if args.database_url_env:
        rp._use_database_env(args.database_url_env)
    import_all_models()
    settings = get_settings()
    host = urlparse(settings.database_url).hostname or "?"
    is_local = host in ("localhost", "127.0.0.1", "::1")
    print(f"database host: {host} ({'local' if is_local else 'REMOTE'})")  # noqa: T201
    sample = bool(args.sample)
    if not sample and not is_local and not args.live and not args.dry_run:
        sys.exit("refusing to write to a remote database without --live (use --dry-run to look first)")
    engine = get_engine()
    work = Path(tempfile.gettempdir()) / "regenerate_slides"

    async with AsyncSession(engine, expire_on_commit=False) as session:
        rows = (
            await session.scalars(
                select(MediaItem).where(MediaItem.kind == "slide_deck").order_by(MediaItem.slug)
            )
        ).all()
        todo = [
            row
            for row in rows
            if (args.sample or args.publish_sample or args.only or "") in row.slug
            and row.content.get("slides")
            and (
                sample
                or args.force
                or args.rerender
                or args.publish_sample
                or row.content.get("narration_voice") != NARRATION_MARK
            )
        ]
        single = sample or bool(args.publish_sample)
        todo = todo[: 1 if single else args.limit] if (single or args.limit) else todo
        print(f"{len(todo)} deck(s) to render")  # noqa: T201
        if args.dry_run:
            for row in todo:
                print(f"would  {row.slug}  {row.title}")  # noqa: T201
            await engine.dispose()
            return 0

    # The reading session is closed here: nothing below holds a connection open through a render.
    failures = 0
    for row in todo:
        label = f"{row.slug}  {row.title}"
        try:
            if args.publish_sample:
                content = _approved_sample(row, args.sample_file)
                video = Path(content["local_video_path"])
                content["final_video_url"] = await asyncio.to_thread(upload_video, settings, video, content)
                await _store(engine, row.id, content)
                print(f"published {label}\n  {content['final_video_url']}", flush=True)  # noqa: T201
                continue
            source = dict(row.content)
            kept = work / f"{row.id}.sample.json"
            if args.force:
                # Fresh words: without this the narration stored on the deck would be used again.
                source.pop("presentation", None)
                source["slides"] = [
                    {key: value for key, value in slide.items() if key != "narration"}
                    for slide in source["slides"]
                ]
            if sample:
                if args.slides:
                    source["slides"] = source["slides"][: args.slides]
                if not args.force:
                    _reuse_sample_narration(source, kept)
            content = await asyncio.to_thread(
                regenerate_slide_av,
                settings,
                source,
                work / str(row.id),
                str(row.id),
                upload=not sample,
                voice_dir=work / "voice",
            )
            if sample:
                kept.write_text(json.dumps(content), encoding="utf-8")
                print(f"SAMPLE video: {content['local_video_path']}")  # noqa: T201
                _print_timeline(content)
                continue
            await _store(engine, row.id, content)
            minutes = content["total_duration"] / 60
            print(f"done   {label}  ({minutes:.1f} min)", flush=True)  # noqa: T201
        except Exception as error:  # noqa: BLE001 - report and carry on with the next deck
            failures += 1
            print(f"FAILED {label}: {error}", flush=True)  # noqa: T201
    await engine.dispose()
    return 1 if failures else 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--sample", help="render one deck whose slug contains this text, locally only")
    parser.add_argument(
        "--slides", type=int, default=4, help="with --sample: only the first N slides (0 = all)"
    )
    parser.add_argument("--publish-sample", help="upload and store the approved sample of this deck")
    parser.add_argument("--sample-file", help="with --publish-sample: the sample's saved json")
    parser.add_argument("--only", help="only decks whose slug contains this text")
    parser.add_argument("--dry-run", action="store_true", help="list what would be rendered")
    parser.add_argument("--database-url-env", help="env var with the database URL, or RAILWAY_PROXY")
    parser.add_argument("--live", action="store_true", help="allow writing to a remote database")
    parser.add_argument("--limit", type=int, help="stop after this many decks")
    parser.add_argument(
        "--rerender", action="store_true", help="redraw decks already done, keeping their words and voice"
    )
    parser.add_argument("--force", action="store_true", help="redo decks already on this narration")
    sys.exit(asyncio.run(_run(parser.parse_args())))


if __name__ == "__main__":
    main()
