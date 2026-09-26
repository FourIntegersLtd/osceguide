"""Creating the exams an import is about to reference.

The four exams used to be inserted by a migration, so an import could assume
they were there. They are authored now, which means the operator running the
import has to say what they are — and saying so is better than assuming: the
timings, the marking rubric and the prompt are decisions somebody should be
making deliberately rather than inheriting from a tuple in a Python file.

The file is a JSON object, one entry per exam:

    {"exams": [{
        "code": "sca",
        "name": "RCGP Simulated Consultation Assessment",
        "default_reading_seconds": 180,
        "default_simulation_seconds": 900,
        "station_attempt_limit": 3,
        "partner_pilot": true,
        "rubric": {
            "title": "SCA marking rubric",
            "system_prompt": "...",
            "pacing": {"total_seconds": 720, "history_seconds": 360,
                       "introduction_seconds": 30, "safety_net_seconds": 120},
            "structure": {"scale": ["R", "A", "G"], "domains": [...], "sections": [...]}
        }
    }]}

Re-running is safe: an exam whose code already exists is left exactly as it is,
rubric included, because a second import must not quietly re-mark anybody.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog import repository as catalog_repository
from app.features.catalog import service_authoring as catalog
from app.features.catalog.models import Exam
from app.features.rubrics import service as rubrics

_DEFAULT_MARKING_LAYOUT: dict[str, Any] = {
    "schemaVersion": 1,
    "sections": [{"id": "sec_main", "title": "Marking", "blocks": []}],
}


class InvalidExamsFile(ValueError):
    """The operator's exams file cannot be used as it stands."""


async def load_exams(session: AsyncSession, spec: Mapping[str, Any], *, now: datetime) -> dict[str, Exam]:
    """Create and publish every exam the file names. Returns them by code."""
    entries = spec.get("exams")
    if not isinstance(entries, list) or not entries:
        raise InvalidExamsFile("The exams file must hold a non-empty `exams` array.")

    exams_by_code: dict[str, Exam] = {}
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise InvalidExamsFile("Each exam must be an object.")
        code = str(entry.get("code") or "").strip().lower()
        if not code:
            raise InvalidExamsFile("Each exam needs a code.")

        existing = await catalog_repository.exam_by_code(session, None, code)
        if existing is not None:
            exams_by_code[code] = existing
            continue

        rubric_version_id = await _publish_rubric(session, entry, code=code, now=now)
        exam = await catalog.create_exam(
            session,
            code=code,
            name=str(entry.get("name") or code.upper()),
            default_reading_seconds=_seconds(entry, "default_reading_seconds", code),
            default_simulation_seconds=_seconds(entry, "default_simulation_seconds", code),
            station_attempt_limit=int(entry.get("station_attempt_limit", 3)),
            rubric_version_id=rubric_version_id,
            partner_pilot=bool(entry.get("partner_pilot", False)),
        )
        await catalog.publish_exam(session, exam.id)
        published_exam = await catalog_repository.exam_by_code(session, None, code)
        assert published_exam is not None
        exams_by_code[code] = published_exam
    return exams_by_code


async def _publish_rubric(
    session: AsyncSession, entry: Mapping[str, Any], *, code: str, now: datetime
) -> uuid.UUID:
    """Create and publish version 1 of one exam's rubric from its entry in the file."""
    rubric = entry.get("rubric")
    if not isinstance(rubric, Mapping):
        raise InvalidExamsFile(
            f"Exam {code!r} has no rubric. An exam that cannot be marked cannot be published, "
            "and imported attempts would have nothing to be re-marked against."
        )
    layout = rubric.get("marking_layout")
    created = await rubrics.create_rubric(
        session,
        None,
        title=str(rubric.get("title") or f"{code} marking rubric"),
        structure=dict(rubric.get("structure") or {}),
        system_prompt=str(rubric.get("system_prompt") or ""),
        pacing=dict(rubric.get("pacing") or {}),
        result_schema_override=rubric.get("result_schema_override"),
        marking_layout=dict(layout) if isinstance(layout, Mapping) else dict(_DEFAULT_MARKING_LAYOUT),
    )
    published = await rubrics.publish_version(session, None, created.id, 1, actor_id=None, now=now)
    return published.id


def _seconds(entry: Mapping[str, Any], key: str, code: str) -> int:
    """A positive whole number of seconds from the entry, or a message naming which exam and field."""
    try:
        value = int(entry[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidExamsFile(f"Exam {code!r} needs a whole number of seconds for {key}.") from exc
    if value <= 0:
        raise InvalidExamsFile(f"Exam {code!r} has a {key} of {value}.")
    return value


def missing_exams(spec: Mapping[str, Any], required: set[str]) -> list[str]:
    """Codes the import will reference that the file does not define.

    Checked before anything is written. The alternative — discovering it
    halfway through — leaves a partial import of somebody's history.
    """
    declared = {
        str(entry.get("code") or "").strip().lower()
        for entry in (spec.get("exams") or [])
        if isinstance(entry, Mapping)
    }
    return sorted(required - declared)
