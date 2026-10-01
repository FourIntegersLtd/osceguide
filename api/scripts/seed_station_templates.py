"""Author and publish the platform's station templates, one per station kind.

    poetry run python scripts/seed_station_templates.py --env staging            # dry run
    poetry run python scripts/seed_station_templates.py --env staging --apply

Seven templates over the four consumer exams: SCA, PLAB 2 and CASC each have
one; Ortho ST3 has four, because its clinical, communication, prioritisation
and portfolio stations are different documents (b2c kept a Pydantic model for
each). Every block of those models' station content is a block here — station
metadata (id, name, created, approved) lives on the station row instead.

The eighth belongs to no exam: "Simulation scenario (ASPiH)", the standard
template an institution copies into its own library, with the faculty sections
a simulation briefing carries. It is written in the seed file only.

`seeds/station-templates.json` is otherwise platform-web's builder presets
(`structureFromStartPoint` in `stationTemplatePresets.ts`) exported as they
stand, so a template seeded here and one an admin starts from the builder are
the same shape. Regenerate it when a preset changes.

Written through `service_templates`, so a structure the API would refuse is
refused here too. Idempotent: a platform template with the same title on the
same exam is left as it is when its latest published structure matches the
seed; when the seed has changed, a new version is published beside it, since
stations already built on the old one keep it until
`link_stations_to_templates.py --upgrade` moves them.

The database URL is read from Railway (`--env`), never typed or printed; with
no `--env` the local `DATABASE_URL` is used.
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
sys.path.insert(0, str(Path(__file__).resolve().parent))

SEED_FILE = Path(__file__).resolve().parents[1] / "seeds/station-templates.json"


class _Rollback(Exception):
    """Ends the transaction without committing. Never escapes `seed`."""


async def seed(*, apply: bool) -> int:
    """Create and publish each missing template in one transaction; roll back unless applying."""
    from sqlalchemy import select

    from app.core.db import get_session_factory, import_all_models
    from app.features.catalog.models import Exam
    from app.features.identity.models import User
    from app.features.stations import repository_templates, service_templates
    from app.features.stations.models import StationTemplate

    import_all_models()
    entries: list[dict[str, Any]] = json.loads(SEED_FILE.read_text())["templates"]
    now = datetime.now(UTC)
    created: list[str] = []
    skipped: list[str] = []
    republished: list[str] = []

    factory = get_session_factory()
    try:
        async with factory() as session, session.begin():
            publisher_id = await session.scalar(
                select(User.id).where(User.is_platform_admin.is_(True)).order_by(User.created_at).limit(1)
            )
            if publisher_id is None:
                raise SystemExit("No platform admin in this database to publish as.")
            for entry in entries:
                label = f"{entry['exam_code'] or 'any exam'}: {entry['title']}"
                same_exam = (
                    StationTemplate.exam_id.is_(None)
                    if entry["exam_code"] is None
                    else StationTemplate.exam_id.in_(select(Exam.id).where(Exam.code == entry["exam_code"]))
                )
                existing = await session.scalar(
                    select(StationTemplate.id).where(
                        StationTemplate.org_id.is_(None),
                        StationTemplate.title == entry["title"],
                        same_exam,
                    )
                )
                if existing is not None:
                    versions = await repository_templates.template_versions(session, None, existing)
                    published = [version for version in versions if version.status == "published"]
                    if published and published[-1].structure == entry["structure"]:
                        skipped.append(label)
                        continue
                    draft = await service_templates.add_version(session, None, existing)
                    await service_templates.edit_version(
                        session, None, existing, draft.version, structure=entry["structure"]
                    )
                    await service_templates.publish_version(
                        session, None, existing, actor_id=publisher_id, now=now
                    )
                    republished.append(f"{label} (v{draft.version})")
                    continue
                template = await service_templates.create_template(
                    session,
                    None,
                    title=entry["title"],
                    exam_code=entry["exam_code"],
                    structure=entry["structure"],
                )
                await service_templates.publish_version(
                    session, None, template.id, actor_id=publisher_id, now=now
                )
                block_count = sum(len(section["blocks"]) for section in entry["structure"]["sections"])
                created.append(
                    f"{label} ({len(entry['structure']['sections'])} sections, {block_count} blocks)"
                )
            if not apply:
                # The same writes, undone: every refusal a real run would hit has been hit.
                raise _Rollback()
    except _Rollback:
        pass

    print("APPLIED" if apply else "dry run, rolled back")  # noqa: T201
    for label in created:
        print(f"  created and published  {label}")  # noqa: T201
    for label in republished:
        print(f"  changed, republished   {label}")  # noqa: T201
    for label in skipped:
        print(f"  already present, left  {label}")  # noqa: T201
    return 0


def main(argv: list[str] | None = None) -> int:
    """Point the app at the chosen database, then seed."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--env", choices=("staging", "production"), help="Railway environment to seed.")
    parser.add_argument("--apply", action="store_true", help="Commit. Without it the run is rolled back.")
    arguments = parser.parse_args(argv)
    if arguments.env:
        from copy_authoring_content import database_url

        # Before any `app` import: settings read DATABASE_URL once.
        os.environ["DATABASE_URL"] = database_url(arguments.env)
    return asyncio.run(seed(apply=arguments.apply))


if __name__ == "__main__":
    sys.exit(main())
