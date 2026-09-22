"""Station authoring use cases.

The lifecycle decisions come from `domain.py`; this maps them onto storage and
translates the domain's refusals into API error codes.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import raise_mapped
from app.features.catalog.errors import UnknownExamError as CatalogUnknownExam
from app.features.catalog.service import resolve_exam
from app.features.stations import domain, domain_content, errors, repository, repository_templates
from app.features.stations import service_templates as templates
from app.features.stations.models import Station, StationVersion
from app.features.stations.refusals import REFUSALS as _REFUSALS
from app.features.stations.schemas import StationRead


async def create_station(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    *,
    title: str,
    exam_code: str,
    content: dict[str, Any],
    template_version_id: uuid.UUID | None = None,
) -> StationRead:
    """A station and its first draft version.

    `template_version_id` binds the station to the shape it was authored
    against. T3: that shape has to be published — a station built on a template
    somebody is still deciding would change under it.
    """
    try:
        exam = await resolve_exam(session, exam_code, org_id=org_id)
    except CatalogUnknownExam as exc:
        # Re-raised as this slice's type so the router documents its own errors.
        raise errors.UnknownExamError(str(exc)) from exc
    if template_version_id is not None:
        await templates.bindable_version(session, org_id, template_version_id)
    station = await repository.create_station(session, org_id, exam_id=exam.id, title=title)
    version = await repository.add_version(
        session,
        org_id,
        station_id=station.id,
        version=1,
        content=content,
        template_version_id=template_version_id,
    )
    # The authoring routes are org-admin only, so the author reads back the
    # whole document they just wrote.
    return _station_read(station, exam.code, version, full_content=True)


async def read_station(session: AsyncSession, org_id: uuid.UUID | None, station_id: uuid.UUID) -> Station:
    station = await repository.station_by_id(session, org_id, station_id)
    if station is None:
        raise errors.StationNotFound()
    return station


async def station_exists(session: AsyncSession, station_id: uuid.UUID) -> bool:
    """Whether any station at all carries this id, whoever owns it.

    Deliberately not org-scoped: a caller below this slice that names a
    station — a community comment's `station_id` — holds no org to scope by,
    and the question it needs answered is existence, not ownership.
    """
    return await repository.exists_by_id(session, station_id)


async def list_stations(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    *,
    limit: int,
    cursor: dict[str, Any] | None,
    full_content: bool,
) -> tuple[list[StationRead], str | None]:
    """The stations this owner has authored.

    `full_content` is the reader-scoped projection (S1): a caller whose only
    relationship to the org is trainee gets each document reduced to what a
    candidate may read — the briefs, the scenario, the doctor's information —
    and never the patient's persona or the examiner's material. Required
    rather than defaulted, so a new call site decides who it is serving
    instead of inheriting the whole document.
    """
    rows, next_cursor = await repository.list_for_org(session, org_id, limit=limit, cursor=cursor)
    out = []
    for station in rows:
        versions = await repository.versions_for_station(session, org_id, station.id)
        latest = versions[-1] if versions else None
        exam = await _exam_code(session, station)
        out.append(_station_read(station, exam, latest, full_content=full_content))
    return out, next_cursor


async def _exam_code(session: AsyncSession, station: Station) -> str:
    from app.features.catalog.service import exam_code_by_id  # noqa: PLC0415 - import cycle

    return await exam_code_by_id(session, station.exam_id) or ""


def _station_read(
    station: Station, exam_code: str, version: StationVersion | None, *, full_content: bool
) -> StationRead:
    content = dict(version.content) if version else None
    if not full_content:
        content = domain_content.candidate_content(content)
    return StationRead(
        id=station.id,
        title=station.title,
        owner_kind=station.owner_kind,
        exam_code=exam_code,
        status=version.status if version else station.status,
        version=version.version if version else 0,
        content=content,
        current_version_id=station.current_version_id,
        template_version_id=version.template_version_id if version else None,
    )


@dataclass(frozen=True)
class RunnableStation:
    """A station resolved for an attempt to run against."""

    version_id: uuid.UUID
    owner_kind: str
    exam_code: str
    title: str
    content: dict[str, Any]
    published: bool
    # The template's ordered block list: what each block of `content` is for.
    # None when the station was written without a template, which the renderer
    # falls back to matching block ids by their common spellings.
    layout: list[dict[str, Any]] | None = None
    # A station whose persona is the examiner rather than the patient — a viva.
    persona: str = "patient"
    greeting: str | None = None


async def runnable_station(
    session: AsyncSession, org_id: uuid.UUID | None, version_id: uuid.UUID
) -> RunnableStation | None:
    """Resolve the station an attempt will be rendered from.

    Lives here because this slice owns what a station looks like. `attempts`
    asks for a scenario and never learns the shape of one, which is the same
    boundary the worker sits behind.
    """
    found = await repository.version_for_attempt(session, org_id, version_id)
    if found is None:
        return None
    version, station = found
    # T4. The rule was written, tested and documented, and nothing called it:
    # `published` was returned here and never read, so a station somebody was
    # still drafting would render and run for a real candidate.
    try:
        domain.ensure_usable_in_circuit(
            domain.VersionRef(number=version.version, status=domain.Status(version.status))
        )
    except domain.LifecycleError as exc:
        raise_mapped(exc, _REFUSALS)
    layout, persona, greeting = await _presentation(session, version.template_version_id)
    return RunnableStation(
        version_id=version.id,
        owner_kind=station.owner_kind,
        exam_code=await _exam_code(session, station),
        title=station.title,
        content=dict(version.content or {}),
        published=version.status == "published",
        layout=layout,
        persona=persona,
        greeting=greeting,
    )


async def _presentation(
    session: AsyncSession, template_version_id: uuid.UUID | None
) -> tuple[list[dict[str, Any]] | None, str, str | None]:
    """How the template says this station should be presented.

    A station bound to no template renders on the block-id conventions, which
    is what keeps stations written before templates working.
    """
    if template_version_id is None:
        return None, "patient", None
    structure = await repository_templates.structure_for_version(session, template_version_id)
    if not structure:
        return None, "patient", None
    blocks = structure.get("blocks")
    if not isinstance(blocks, list):
        blocks = [
            block
            for section in structure.get("sections") or []
            if isinstance(section, dict)
            for block in (section.get("blocks") or [])
            if isinstance(block, dict)
        ]
    presentation = structure.get("layout") or {}
    layout = [dict(b) for b in blocks if isinstance(b, dict)] if isinstance(blocks, list) else None
    persona = str(presentation.get("persona") or "patient")
    greeting = presentation.get("greeting")
    return layout, persona, (str(greeting) if greeting else None)
