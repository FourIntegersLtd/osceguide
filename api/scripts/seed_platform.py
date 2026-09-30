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

    PYTHONPATH=. python scripts/seed_platform.py --republish --env staging --dry-run

`--republish` is the one exception, for a database seeded before the starter
file changed (the version 2 rubric structure, the legacy wording). Where an
existing exam's rubric differs from the seed (its structure or its marking
prompt), the seed's rubric is published as a new version of that rubric and the
exam is repointed at it. The marking layout is kept. An exam whose rubric
already matches is left alone, so a second run writes nothing. Attempts
already rendered keep the version they froze.

What it deliberately does not do:

- **Invent score anchors.** Only SCA's legacy models said what earns G, A
  and R on each competency; PLAB 2, CASC and Ortho said what to assess, which
  is carried as each competency's instructions. `--report` lists the competencies with no anchors,
  for a clinician to write.
- **Import no stations.** The library comes from Firestore, not from here:
  put the four `*stations` collections in `stations.json` and
  `scripts/migrate_legacy.py` loads them. Run this first — a station
  whose exam does not exist yet is reported, not invented.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import get_session_factory, import_all_models  # noqa: E402
from app.core.exam_settings import ExamSettings  # noqa: E402
from app.features.catalog import service as catalog  # noqa: E402
from app.features.catalog import service_authoring as exams  # noqa: E402
from app.features.catalog.errors import UnknownExamError  # noqa: E402
from app.features.rubrics import service as rubrics  # noqa: E402
from app.features.rubrics import service_marking as rubric_versions  # noqa: E402

DEFAULT_MARKING_LAYOUT: dict[str, Any] = {
    "schemaVersion": 1,
    "sections": [{"id": "sec_main", "title": "Marking", "blocks": []}],
}


_ORTHO_SUBTYPES = ("clinical", "communication", "prioritisation", "portfolio")

# How each platform exam differs apart from its rubric, stored in `exams.settings`.
# The same values the `u2v3w4x5y6z7` migration backfilled into existing databases;
# an exam not named here gets `{}`, which reads back as every default.
PLATFORM_EXAM_SETTINGS: dict[str, ExamSettings] = {
    "sca": ExamSettings.model_validate(
        {
            "show_tips_while_marking": True,
            "help_modes": ["navigate", "knowledge_base"],
            "peer_waiting_email": True,
        }
    ),
    "plab": ExamSettings.model_validate(
        {
            "generation": {
                "station_prompt": "plab.station",
                "summary_prompt": "sca.summary",
                "blog_prompt": "plab.blog",
                "default_profile": "plab.station",
            }
        }
    ),
    "casc": ExamSettings.model_validate(
        {
            "generation": {
                "station_prompt": "casc.station",
                "summary_prompt": "casc.summary",
                "blog_prompt": "sca.blog",
                "default_profile": "casc.station",
            }
        }
    ),
    "ortho": ExamSettings.model_validate(
        {
            "date_label": "Interview date",
            "session_modes": ["debrief"],
            "station_subtypes": [
                {"key": subtype, "label": subtype.capitalize(), "generation_profile": f"ortho.{subtype}"}
                for subtype in _ORTHO_SUBTYPES
            ],
            "generation": {
                "station_prompt": "ortho.clinical",
                "summary_prompt": "sca.summary",
                "blog_prompt": "sca.blog",
                "default_profile": "ortho.clinical",
            },
        }
    ),
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
    """Competencies of an enumerated rating with no anchors, named so a clinician can write them.

    A range or boolean rating has no values to anchor, so it never has gaps.
    """
    rating = structure.get("rating") or {}
    if rating.get("kind") not in ("rag", "scale"):
        return []
    missing = []
    for section in structure.get("sections", []):
        if section.get("kind") != "domain":
            continue
        for competency in section.get("competencies", []):
            if not competency.get("descriptors"):
                missing.append(f"{section.get('id')}.{competency.get('id')}")
    return missing


def needs_republish(stored_structure: dict[str, Any], stored_prompt: str, spec: dict[str, Any]) -> bool:
    """Whether the seed's rubric differs from the one an exam is bound to.

    Compared as stored JSON, so a version 1 structure always differs from the
    version 2 seed, and a rubric republished once matches on the next run.
    """
    return stored_structure != spec["structure"] or stored_prompt != spec["system_prompt"]


async def republish_existing(session: Any, code: str, spec: dict[str, Any], now: datetime) -> bool:
    """Publish the seed's rubric as a new version of `code`'s rubric, and repoint the exam at it.

    False when the bound rubric already matches the seed, so nothing is written.
    """
    exam = await catalog.resolve_exam(session, code)
    if exam.rubric_version_id is None:
        return False
    current = await rubric_versions.published_platform_version(session, exam.rubric_version_id)
    if not needs_republish(dict(current.structure or {}), current.system_prompt, spec):
        return False
    draft = await rubrics.add_version(session, None, current.rubric_id)
    # Every body field passed explicitly: add_version seeds from the latest
    # published version, which need not be the one this exam is bound to.
    await rubrics.edit_version(
        session,
        None,
        current.rubric_id,
        draft.version,
        structure=spec["structure"],
        system_prompt=spec["system_prompt"],
        pacing=dict(spec["pacing"]),
        marking_layout=current.marking_layout,
    )
    published = await rubrics.publish_version(
        session, None, current.rubric_id, draft.version, actor_id=None, now=now
    )
    await exams.update_exam(session, exam.id, rubric_version_id=published.id)
    return True


async def seed(*, path: Path, dry_run: bool, report: bool, republish: bool = False) -> int:
    """Author every exam in the seed file that is missing; with `republish`, bring existing ones up to it."""
    import_all_models()
    entries = load(path)
    now = datetime.now(UTC)
    created, skipped, republished, gaps = [], [], [], {}

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
                    # Left exactly as it is — a second run must not re-mark
                    # anybody, nor replace a rubric since edited — unless
                    # asked to republish the seed's rubric.
                    if republish and await republish_existing(session, code, entry["rubric"], now):
                        republished.append(code)
                    else:
                        skipped.append(code)
                    missing = undescribed(entry["rubric"]["structure"])
                    if missing:
                        gaps[code] = missing
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
                    settings=PLATFORM_EXAM_SETTINGS.get(code),
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

    return _report(created, skipped, republished, gaps, dry_run=dry_run, report=report)


class _Rollback(Exception):
    """Ends the transaction without committing. Never escapes `seed`."""


def _report(
    created: list[str],
    skipped: list[str],
    republished: list[str],
    gaps: dict[str, list[str]],
    *,
    dry_run: bool,
    report: bool,
) -> int:
    verb = "would create" if dry_run else "created"
    print(f"{verb}: {', '.join(created) or 'nothing'}")  # noqa: T201
    if republished:
        verb = "would republish" if dry_run else "republished, new version bound"
        print(f"{verb}: {', '.join(republished)}")  # noqa: T201
    if skipped:
        print(f"already present, left untouched: {', '.join(skipped)}")  # noqa: T201
    total_gaps = sum(len(v) for v in gaps.values())
    if total_gaps:
        print(  # noqa: T201
            f"\n{total_gaps} competencies have instructions but no G/A/R anchors: the legacy "
            "models never had them. They mark on the instructions and the prompt; a "
            "clinician writing anchors would make each score explicit."
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
    parser.add_argument(
        "--republish",
        action="store_true",
        help="Publish the seed's rubric as a new version where an existing exam's differs, and repoint it.",
    )
    parser.add_argument("--env", choices=("staging", "production"), help="Railway environment to seed.")
    args = parser.parse_args(argv)
    if args.env:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from copy_authoring_content import database_url

        # Before the session factory is built: settings read DATABASE_URL once.
        os.environ["DATABASE_URL"] = database_url(args.env)
    try:
        return asyncio.run(
            seed(path=args.file, dry_run=args.dry_run, report=args.report, republish=args.republish)
        )
    except SeedFileInvalid as exc:
        print(f"error: {exc}", file=sys.stderr)  # noqa: T201
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
