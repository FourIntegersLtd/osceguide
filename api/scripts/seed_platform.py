"""Author the platform's own exams and rubrics into an empty database.

    python scripts/seed_platform.py --file seeds/platform-starter.json --dry-run
    make seed-platform

A migrated database is empty: no exams, no rubrics, no station library, and
nothing seeds any of it any more (ADR 0016 — exams and rubrics are authored
data, not shipped code). That is the right default for an institution, which
authors its own. It is the wrong default for *our* four consumer exams, which
have existed for years and whose domain ids results are already stored
against.

So this is not a fixture. It replays the platform catalogue that b2c has been
marking against all along: the domain and competency ids come from the legacy
feedback models and the system prompt from the legacy marking prompt, both
captured in `tests/fixtures/`. Getting those ids right is what keeps a
migrated result comparable with one marked next week.

Idempotent by design, and safe to re-run: an exam whose code already exists is
left exactly as it is, rubric included. A second run must never re-mark
anybody, and must never quietly replace a rubric a human has since edited.

What it deliberately does not do:

- **Publish nothing it cannot fill in.** Descriptors are empty in the starter
  file, because today the marking wording lives inside the system prompt
  rather than per competency. The rubric is still published, since the prompt
  is what the model actually reads, but `--report` tells you which
  competencies a human still needs to write descriptors for before live
  marking means anything.
- **Import no stations.** The library comes from Firestore, not from here:
  put the four `*stations` collections in `stations.json` and
  `scripts/migrate_legacy.py` loads them. Run this first — a station
  whose exam does not exist yet is reported, not invented.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import get_session_factory, import_all_models  # noqa: E402
from app.features.catalog import service as catalog  # noqa: E402
from app.features.catalog import service_authoring as exams  # noqa: E402
from app.features.catalog.errors import UnknownExamError  # noqa: E402
from app.features.rubrics import service as rubrics  # noqa: E402

DEFAULT_MARKING_LAYOUT: dict[str, Any] = {
    "schemaVersion": 1,
    "sections": [{"id": "sec_main", "title": "Marking", "blocks": []}],
}


class SeedFileInvalid(Exception):
    """The file does not describe exams this script can author."""


def load(path: Path) -> list[dict[str, Any]]:
    try:
        raw = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SeedFileInvalid(f"{path}: {exc}") from exc
    entries = raw.get("exams") if isinstance(raw, dict) else raw
    if not isinstance(entries, list) or not entries:
        raise SeedFileInvalid(f"{path}: expected a non-empty 'exams' list.")
    for entry in entries:
        missing = {"code", "name", "rubric"} - set(entry)
        if missing:
            raise SeedFileInvalid(f"{path}: an exam is missing {sorted(missing)}.")
    return entries


def undescribed(structure: dict[str, Any]) -> list[str]:
    """Competencies with no descriptors, named so a human can finish them."""
    out = []
    for domain in structure.get("domains", []):
        for competency in domain.get("competencies", []):
            if not competency.get("descriptors"):
                out.append(f"{domain.get('id')}.{competency.get('id')}")
    return out


async def seed(*, path: Path, dry_run: bool, report: bool) -> int:
    import_all_models()
    entries = load(path)
    now = datetime.now(UTC)
    created, skipped, gaps = [], [], {}

    factory = get_session_factory()
    try:
        async with factory() as session, session.begin():
            for entry in entries:
                code = str(entry["code"])
                try:
                    await catalog.resolve_exam(session, code)
                except UnknownExamError:
                    pass
                else:
                    # Left exactly as it is. A second run must not re-mark
                    # anybody, and must not replace a rubric since edited.
                    skipped.append(code)
                    continue

                spec = entry["rubric"]
                rubric = await rubrics.create_rubric(
                    session,
                    None,
                    title=spec["title"],
                    structure=spec["structure"],
                    system_prompt=spec["system_prompt"],
                    pacing=spec["pacing"],
                    marking_layout=spec.get("marking_layout") or DEFAULT_MARKING_LAYOUT,
                )
                published = await rubrics.publish_version(session, None, rubric.id, 1, actor_id=None, now=now)
                exam = await exams.create_exam(
                    session,
                    None,
                    code=code,
                    name=entry["name"],
                    default_reading_seconds=int(entry.get("default_reading_seconds", 120)),
                    default_simulation_seconds=int(entry.get("default_simulation_seconds", 600)),
                    station_attempt_limit=int(entry.get("station_attempt_limit", 3)),
                    rubric_version_id=published.id,
                )
                await exams.publish_exam(session, exam.id)
                created.append(code)
                missing = undescribed(spec["structure"])
                if missing:
                    gaps[code] = missing

            if dry_run:
                # The same code path, rolled back — so every constraint a real
                # run would hit has been hit by the time this prints.
                raise _Rollback()

    except _Rollback:
        pass

    return _report(created, skipped, gaps, dry_run=dry_run, report=report)


class _Rollback(Exception):
    """Ends the transaction without committing. Never escapes `seed`."""


def _report(
    created: list[str], skipped: list[str], gaps: dict[str, list[str]], *, dry_run: bool, report: bool
) -> int:
    verb = "would create" if dry_run else "created"
    print(f"{verb}: {', '.join(created) or 'nothing'}")  # noqa: T201
    if skipped:
        print(f"already present, left untouched: {', '.join(skipped)}")  # noqa: T201
    total_gaps = sum(len(v) for v in gaps.values())
    if total_gaps:
        print(  # noqa: T201
            f"\n{total_gaps} competencies have no descriptors. The marking prompt still "
            "carries the wording, so these rubrics mark; but live marking and any "
            "per-competency feedback need a human to write them."
        )
        if report:
            for code, names in sorted(gaps.items()):
                print(f"  {code}:")  # noqa: T201
                for name in names:
                    print(f"    {name}")  # noqa: T201
        else:
            print("  Re-run with --report to list them.")  # noqa: T201
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, default=Path("seeds/platform-starter.json"))
    parser.add_argument("--dry-run", action="store_true", help="Roll back instead of committing.")
    parser.add_argument("--report", action="store_true", help="List every undescribed competency.")
    args = parser.parse_args(argv)
    try:
        return asyncio.run(seed(path=args.file, dry_run=args.dry_run, report=args.report))
    except SeedFileInvalid as exc:
        print(f"error: {exc}", file=sys.stderr)  # noqa: T201
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
