"""Turning an attempt into the definition a worker and a marker can both use.

Two things are decided here and frozen together: the instructions the live
persona is given, and the rubric the transcript will be marked against. They
are frozen because both must survive the station being edited and the rubric
being superseded — a candidate is assessed against what they were shown and
what they were told they would be marked on, not against today's version.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.logging import get_logger
from app.core.ports import RenderFailed
from app.core.settings import get_settings
from app.features.attempts import domain, domain_definition, errors, repository
from app.features.attempts.jobs import PLATFORM_DEFAULT_POLICY
from app.features.attempts.models import Attempt
from app.features.attempts.renderer import build_renderer
from app.features.catalog import service as catalog
from app.features.rubrics import service_marking as rubrics
from app.features.sittings import service as sittings_service
from app.features.stations import service as stations

log = get_logger(__name__)

_MODE_FOR_KIND = {"debrief": "tutor", "examiner": "examiner"}


async def render_definition(session: AsyncSession, attempt: Attempt, *, now: datetime) -> dict[str, Any]:
    """Render the attempt's definition, and freeze it if the render was real.

    A1/A2. The definition is frozen once, on the first *successful* render.
    Both legacy backends freeze unconditionally, which is why an unresolved
    station there pins a generic patient prompt to the attempt forever — the
    candidate then talks to nobody in particular for the whole session, and
    every replay of it shows the same.

    A degraded render is still served, so a session is never blocked by it, but
    it is not persisted: the next bootstrap tries again, and once the station
    is fixed the attempt gets the real thing.
    """
    station = None
    if attempt.station_version_id is not None:
        station = await stations.runnable_station(session, attempt.org_id, attempt.station_version_id)
    if station is None:
        raise errors.AttemptNotReady(
            "This attempt has no station to run against, so there is nothing to render."
        )

    exam = await catalog.exam_for_attempt(session, attempt.exam_id)
    degraded = not domain_definition.scenario_is_renderable(station.content, station.layout)
    mode = station.persona if station.persona != "patient" else _MODE_FOR_KIND.get(attempt.kind, "patient")

    try:
        rendered = build_renderer().render(
            station={"title": station.title, "content": station.content},
            layout=station.layout,
            greeting=station.greeting,
            mode=mode,
        )
    except RenderFailed as exc:
        raise errors.AttemptNotReady(str(exc)) from exc

    rubric = await _marking_snapshot(session, attempt, exam)

    scenario = domain_definition.scenario_payload(
        scenario_id=str(station.version_id),
        scenario_source="org" if station.owner_kind == "org" else "library",
        title=station.title,
        content=station.content,
        examiner_context=str(context) if (context := rendered.get("examiner_context")) else None,
    )
    payload = domain_definition.definition_payload(
        attempt_id=str(attempt.id),
        framework_id=str((rubric or {}).get("framework", {}).get("id") or ""),
        scenario_source=str(scenario["source"]),
        scenario_id=str(scenario["id"]),
        scenario=scenario,
        voice=scenario["patient_gender"],
        instructions=str(rendered["instructions"]),
        greeting=str(greeting) if (greeting := rendered.get("greeting")) else None,
        mode=mode,
        policy_version=PLATFORM_DEFAULT_POLICY,
        primary_model=get_settings().marking_primary_model,
        at=now,
        rubric=rubric,
    )

    if domain.should_freeze(render_degraded=degraded, already_frozen=bool(attempt.definition)):
        await repository.freeze_definition(session, attempt.id, definition=payload, at=now)
    else:
        log.warning(
            "serving a degraded render without freezing it",
            attempt_id=str(attempt.id),
            station_version_id=str(station.version_id),
        )
    return payload


async def _marking_snapshot(session: AsyncSession, attempt: Attempt, exam: Any) -> dict[str, Any] | None:
    """The rubric this attempt will be marked against, frozen onto it.

    Slot attempts use the sitting's bound rubric version; everything else uses
    the exam's published rubric.

    A missing or unpublished rubric is not fatal here: the session still runs
    and is still recorded. It is `enqueue_scoring` that refuses to queue a
    marking it cannot perform, which is the right place for that refusal.
    """
    rubric_version_id = exam.rubric_version_id
    if attempt.slot_id is not None:
        bound = await sittings_service.rubric_version_for_slot(session, attempt.org_id, attempt.slot_id)
        if bound is not None:
            rubric_version_id = bound
    if rubric_version_id is None:
        log.warning("attempt has no rubric to be marked against", attempt_id=str(attempt.id))
        return None
    try:
        return await rubrics.marking_snapshot(
            session,
            attempt.org_id,
            rubric_version_id=rubric_version_id,
            field_selection=None,
        )
    except AppError as exc:
        log.warning("rubric unavailable for attempt", attempt_id=str(attempt.id), reason=str(exc))
        return None
