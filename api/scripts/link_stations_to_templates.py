"""Bind the platform's library stations to the station template they were written to.

    poetry run python scripts/link_stations_to_templates.py --env staging            # dry run
    poetry run python scripts/link_stations_to_templates.py --env staging --apply

The imported b2c stations were authored to the same models the seeded platform
templates were built from (`seed_station_templates.py`), one per exam and four
for Ortho ST3, whose stations say which kind they are in `station_type`. This
sets each of their versions' `template_version_id` to that template's latest
published version, so the station reads as generated from it.

A bound station renders through its template's layout, and
`domain_content.content_for_template` reads the nested b2c sections by block
id. Every bound station is rendered here before anything commits: it must stay
renderable, no examiner block may reach a patient's prompt, and an examiner
(Ortho's viva) must hold every one of its questions. One failure rolls the
whole run back.

Ortho needs osce-assessment 0.9.0, the first engine that gives the examiner
persona its `examiner` blocks.

Idempotent: a version already bound to a template is left as it is.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

# The seeded template each exam's stations were written to; Ortho's is chosen
# per station by its `station_type`.
TEMPLATE_TITLES = {
    "sca": "SCA consultation station",
    "plab": "PLAB 2 station",
    "casc": "CASC station",
}
ORTHO_TITLES = {
    "clinical": "Ortho ST3 clinical",
    "communication": "Ortho ST3 communication",
    "prioritisation": "Ortho ST3 prioritisation",
    "portfolio": "Ortho ST3 portfolio",
}


class _Rollback(Exception):
    """Ends the transaction without committing. Never escapes `link`."""


def _template_title(exam_code: str, content: dict[str, Any]) -> str | None:
    """Which template a station was written to, or None when it names no known kind."""
    if exam_code == "ortho":
        return ORTHO_TITLES.get(str(content.get("station_type") or "").strip().lower())
    return TEMPLATE_TITLES.get(exam_code)


async def link(*, apply: bool) -> int:
    """Bind, prove every bound station still renders, and commit only when applying and proven."""
    from osce_assessment.prompts import create_station_prompt, station_examiner_context
    from sqlalchemy import select, text

    from app.core.db import get_session_factory, import_all_models
    from app.features.attempts.domain_definition import scenario_is_renderable
    from app.features.catalog.models import Exam
    from app.features.stations import service as stations_service
    from app.features.stations.models import Station, StationTemplate, StationTemplateVersion, StationVersion

    import_all_models()
    bound: Counter[str] = Counter()
    already: Counter[str] = Counter()
    unmatched: list[str] = []
    failures: list[str] = []

    factory = get_session_factory()
    try:
        async with factory() as session, session.begin():
            # Latest published version of each platform template, by (exam, title).
            template_versions: dict[tuple[str, str], uuid.UUID] = {}
            template_rows = await session.execute(
                select(Exam.code, StationTemplate.title, StationTemplateVersion.id)
                .join(StationTemplate, StationTemplate.exam_id == Exam.id)
                .join(StationTemplateVersion, StationTemplateVersion.template_id == StationTemplate.id)
                .where(StationTemplate.org_id.is_(None), StationTemplateVersion.status == "published")
                .order_by(StationTemplateVersion.version)
            )
            for exam_code, title, version_id in template_rows:
                template_versions[(exam_code, title)] = version_id

            station_rows = await session.execute(
                select(Station.id, Station.title, Station.current_version_id, Exam.code)
                .join(Exam, Exam.id == Station.exam_id)
                .where(Station.org_id.is_(None))
            )
            stations = list(station_rows)
            for station_id, station_title, current_version_id, exam_code in stations:
                versions = (
                    await session.scalars(
                        select(StationVersion).where(StationVersion.station_id == station_id)
                    )
                ).all()
                current = next((version for version in versions if version.id == current_version_id), None)
                reference = current or (versions[-1] if versions else None)
                title = _template_title(exam_code, dict(reference.content or {})) if reference else None
                template_version_id = template_versions.get((exam_code, title)) if title else None
                if template_version_id is None:
                    unmatched.append(f"{exam_code}: {station_title}")
                    continue
                label = f"{exam_code}: {title}"
                unbound = [version.id for version in versions if version.template_version_id is None]
                if not unbound:
                    already[label] += 1
                    continue
                await session.execute(
                    text("UPDATE station_versions SET template_version_id = :bound WHERE id = ANY(:ids)"),
                    {"bound": template_version_id, "ids": unbound},
                )
                bound[label] += 1

            # The proof: every platform station renders as a worker would get it.
            session.expire_all()
            for _station_id, station_title, current_version_id, exam_code in stations:
                if current_version_id is None:
                    continue
                station = await stations_service.runnable_station(session, None, current_version_id)
                if station is None or station.layout is None:
                    continue
                name = f"{exam_code}: {station_title}"
                if not scenario_is_renderable(station.content, station.layout, station.persona):
                    failures.append(f"{name} — not renderable")
                    continue
                rendered = {"title": station.title, "content": station.content}
                prompt = create_station_prompt(rendered, station.layout, persona=station.persona)
                examiner = station_examiner_context(rendered, station.layout) or ""
                # Text an author also gave a non-examiner block (findings the
                # patient reveals on examination) is the patient's to say.
                own_text = json.dumps(
                    [
                        station.content.get(str(block.get("id")))
                        for block in station.layout
                        if block.get("role") != "examiner"
                    ]
                )
                examiner_lines = [
                    line.strip()
                    for line in examiner.splitlines()
                    if len(line.strip()) > 40 and not line.startswith("<") and line.strip() not in own_text
                ]
                if station.persona == "examiner":
                    # A viva's examiner must hold the questions it asks.
                    if not examiner_lines or not all(line in prompt for line in examiner_lines):
                        failures.append(f"{name} — the examiner is missing its questions")
                elif any(line in prompt for line in examiner_lines):
                    failures.append(f"{name} — examiner material in the patient prompt")
            if failures or not apply:
                raise _Rollback()
    except _Rollback:
        pass

    print("APPLIED" if apply and not failures else "rolled back")  # noqa: T201
    for label, count in sorted(bound.items()):
        print(f"  bound          {count:4}  {label}")  # noqa: T201
    for label, count in sorted(already.items()):
        print(f"  already bound  {count:4}  {label}")  # noqa: T201
    for name in unmatched:
        print(f"  no template    {name}")  # noqa: T201
    for failure in failures:
        print(f"  FAILED         {failure}")  # noqa: T201
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    """Point the app at the chosen database, then link."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--env", choices=("staging", "production"), help="Railway environment to link.")
    parser.add_argument("--apply", action="store_true", help="Commit. Without it the run is rolled back.")
    arguments = parser.parse_args(argv)
    if arguments.env:
        from copy_authoring_content import database_url

        # Before any `app` import: settings read DATABASE_URL once.
        os.environ["DATABASE_URL"] = database_url(arguments.env)
    return asyncio.run(link(apply=arguments.apply))


if __name__ == "__main__":
    sys.exit(main())
