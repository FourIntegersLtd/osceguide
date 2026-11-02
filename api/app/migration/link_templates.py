"""Bind library stations to the station template they were written to.

The imported b2c stations were authored to the same models the seeded platform templates were
built from (`seed_station_templates.py`), one per exam and four for Ortho ST3, whose stations say
which kind they are in `station_type`. This sets each unbound version's `template_version_id` to
that template's latest published version, so the station renders through the template's layout
(`attempts/service_material.py` reads a brief/review this way) instead of with no brief at all.

Every bound station is proven still renderable before the caller commits: no examiner block may
reach a patient's brief, and an examiner persona (Ortho's viva) must hold every question it asks.
A failure is reported, never silently left bound; the caller decides whether to keep the change.
"""

from __future__ import annotations

import json
import uuid
from collections import Counter

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts.domain_definition import scenario_is_renderable
from app.features.catalog.models import Exam
from app.features.stations import service as stations_service
from app.features.stations.models import Station, StationTemplate, StationTemplateVersion, StationVersion
from app.migration.b2c_lookups import StepReport

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


def _template_title(exam_code: str, content: dict) -> str | None:
    """Which template a station was written to, or None when it names no known kind."""
    if exam_code == "ortho":
        return ORTHO_TITLES.get(str(content.get("station_type") or "").strip().lower())
    return TEMPLATE_TITLES.get(exam_code)


async def bind_unbound_versions(session: AsyncSession, *, upgrade: bool = False) -> StepReport:
    """Bind every station version with no template, then prove each bound station still renders.

    `upgrade` also moves a version bound to an older published version of the same template onto
    its latest, once `seed_station_templates.py` has published a changed structure. Nothing here
    commits or rolls back; the caller's transaction decides what to keep.
    """
    from osce_assessment.prompts import create_station_prompt, station_examiner_context

    report = StepReport()
    bound: Counter[str] = Counter()
    already: Counter[str] = Counter()

    template_versions: dict[tuple[str, str], uuid.UUID] = {}
    every_version: dict[tuple[str, str], set[uuid.UUID]] = {}
    template_rows = await session.execute(
        select(Exam.code, StationTemplate.title, StationTemplateVersion.id)
        .join(StationTemplate, StationTemplate.exam_id == Exam.id)
        .join(StationTemplateVersion, StationTemplateVersion.template_id == StationTemplate.id)
        .where(StationTemplate.org_id.is_(None), StationTemplateVersion.status == "published")
        .order_by(StationTemplateVersion.version)
    )
    for exam_code, title, version_id in template_rows:
        template_versions[(exam_code, title)] = version_id
        every_version.setdefault((exam_code, title), set()).add(version_id)

    station_rows = await session.execute(
        select(Station.id, Station.title, Station.current_version_id, Exam.code)
        .join(Exam, Exam.id == Station.exam_id)
        .where(Station.org_id.is_(None))
    )
    stations = list(station_rows)
    for station_id, station_title, current_version_id, exam_code in stations:
        versions = (
            await session.scalars(select(StationVersion).where(StationVersion.station_id == station_id))
        ).all()
        current = next((version for version in versions if version.id == current_version_id), None)
        reference = current or (versions[-1] if versions else None)
        title = _template_title(exam_code, dict(reference.content or {})) if reference else None
        template_version_id = template_versions.get((exam_code, title)) if title else None
        if template_version_id is None:
            report.problem(f"{exam_code}: {station_title}: no matching template")
            continue
        label = f"{exam_code}: {title}"
        existing = every_version.get((exam_code, title or ""), set())
        older = existing - {template_version_id} if upgrade else set()
        unbound = [
            version.id
            for version in versions
            if version.template_version_id is None or version.template_version_id in older
        ]
        if not unbound:
            already[label] += 1
            continue
        await session.execute(
            text("UPDATE station_versions SET template_version_id = :bound WHERE id = ANY(:ids)"),
            {"bound": template_version_id, "ids": unbound},
        )
        bound[label] += 1

    session.expire_all()
    for _station_id, station_title, current_version_id, exam_code in stations:
        if current_version_id is None:
            continue
        station = await stations_service.runnable_station(session, None, current_version_id)
        if station is None or station.layout is None:
            continue
        name = f"{exam_code}: {station_title}"
        leaked = [
            block.id for section in station.sections for block in section.blocks if block.role == "examiner"
        ]
        if leaked:
            report.problem(f"{name}: examiner material in the candidate brief: {', '.join(leaked)}")
        if not scenario_is_renderable(station.content, station.layout, station.persona):
            report.problem(f"{name}: not renderable")
            continue
        rendered = {"title": station.title, "content": station.content}
        prompt = create_station_prompt(rendered, station.layout, persona=station.persona)
        examiner = station_examiner_context(rendered, station.layout) or ""
        own_blocks = [block for block in station.layout if block.get("role") != "examiner"]
        own_text = json.dumps([station.content.get(str(block.get("id"))) for block in own_blocks])
        examiner_lines = [
            line.strip()
            for line in examiner.splitlines()
            if len(line.strip()) > 40 and not line.startswith("<") and line.strip() not in own_text
        ]
        if station.persona == "examiner":
            if not examiner_lines or not all(line in prompt for line in examiner_lines):
                report.problem(f"{name}: the examiner is missing its questions")
        elif any(line in prompt for line in examiner_lines):
            report.problem(f"{name}: examiner material in the patient prompt")

    for label, count in bound.items():
        report.count(f"bound to {label}", count)
    for label, count in already.items():
        report.count(f"already bound to {label}", count)
    return report
