"""Station authoring use cases.

The lifecycle decisions come from `domain.py`; this maps them onto storage and
translates the domain's refusals into API error codes.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import raise_mapped
from app.features.catalog.errors import UnknownExamError as CatalogUnknownExam
from app.features.catalog.service import resolve_exam
from app.features.stations import (
    domain,
    domain_audience,
    domain_content,
    errors,
    repository,
    repository_templates,
)
from app.features.stations import service_templates as templates
from app.features.stations.models import Station, StationVersion
from app.features.stations.refusals import REFUSALS as _REFUSALS
from app.features.stations.schemas import AudienceBlockRead, AudienceSectionRead, RecordFieldRead, StationRead


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
    return await _station_read(session, station, exam.code, version, full_content=True)


async def read_station(session: AsyncSession, org_id: uuid.UUID | None, station_id: uuid.UUID) -> Station:
    """One station this org owns, or refuse if there is no such station."""
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
    search: str | None = None,
    exam_code: str | None = None,
    include_archived: bool = False,
) -> tuple[list[StationRead], str | None]:
    """The stations this owner has authored.

    `full_content` is the reader-scoped projection (S1): a caller whose only relationship to the org
    is trainee gets each document reduced to what a candidate may read, never the patient's persona
    or the examiner's material. Required rather than defaulted, so a new call site must decide who
    it is serving. `search` is a title fragment, answered in SQL rather than by walking every page.
    `exam_code` narrows to one exam; a code this owner may not resolve answers an empty page rather
    than a catalogue error, since this is a list filter, not authoring input. `include_archived`
    excludes archived stations by default.
    """
    exam_id = None
    if exam_code is not None:
        try:
            exam_id = (await resolve_exam(session, exam_code, org_id=org_id)).id
        except CatalogUnknownExam:
            return [], None
    stations, next_cursor = await repository.list_for_org(
        session,
        org_id,
        limit=limit,
        cursor=cursor,
        exam_id=exam_id,
        search=search,
        include_archived=include_archived,
    )
    station_reads = []
    for station in stations:
        versions = await repository.versions_for_station(session, org_id, station.id)
        latest = versions[-1] if versions else None
        exam = await _exam_code(session, station)
        station_reads.append(await _station_read(session, station, exam, latest, full_content=full_content))
    return station_reads, next_cursor


async def _exam_code(session: AsyncSession, station: Station) -> str:
    """The exam code this station's exam id resolves to, or empty if it no longer does."""
    from app.features.catalog.service import exam_code_by_id  # noqa: PLC0415 - import cycle

    return await exam_code_by_id(session, station.exam_id) or ""


async def _station_read(
    session: AsyncSession,
    station: Station,
    exam_code: str,
    version: StationVersion | None,
    *,
    full_content: bool,
) -> StationRead:
    """Map a station and its latest version onto the schema, projected for the reader's audience.

    A trainee-only reader (`full_content=False`) gets the document reduced to
    what the candidate audience of its template may see. A version bound to no
    template — or whose template has no structure — falls back to
    `domain_content.candidate_content`'s named-key allowlist, which is what
    every station written before templates existed still is.
    """
    content = dict(version.content) if version else None
    if not full_content and content is not None and version is not None:
        content = await _candidate_projection(session, version, content)
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


async def _candidate_projection(
    session: AsyncSession, version: StationVersion, content: dict[str, Any]
) -> dict[str, Any]:
    """A version's content reduced to the candidate audience, by its template when it has one."""
    sections = await audience_sections(session, version.template_version_id, content, ("candidate",))
    if sections:
        return {block.id: block.value for section in sections for block in section.blocks}
    return domain_content.candidate_content(content) or {}


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
    # The candidate audience's sections, for the worker's `candidate_brief`
    # text contract (`domain_definition.scenario_payload`). Empty when the
    # station carries no template.
    sections: list[domain_audience.AudienceSection] = field(default_factory=list)


async def runnable_station(
    session: AsyncSession, org_id: uuid.UUID | None, version_id: uuid.UUID
) -> RunnableStation | None:
    """Resolve the station an attempt will be rendered from.

    `attempts` asks for a scenario and never learns the shape of one — the same boundary the worker
    sits behind.
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
    layout, persona, greeting, content, sections = await _presentation(
        session, version.template_version_id, dict(version.content or {})
    )
    candidate_sections = domain_audience.sections_for(sections, content, "candidate") if sections else []
    return RunnableStation(
        version_id=version.id,
        owner_kind=station.owner_kind,
        exam_code=await _exam_code(session, station),
        title=station.title,
        content=content,
        published=version.status == "published",
        layout=layout,
        persona=persona,
        greeting=greeting,
        sections=candidate_sections,
    )


async def _presentation(
    session: AsyncSession, template_version_id: uuid.UUID | None, content: dict[str, Any]
) -> tuple[list[dict[str, Any]] | None, str, str | None, dict[str, Any], list[Any]]:
    """How the template says this station should be presented, and its content as the blocks read it.

    A station bound to no template renders on the block-id conventions, which
    is what keeps stations written before templates working. The fifth
    element is the template's raw section list, for a caller that needs the
    audience projections (`audience_sections`, and `runnable_station`'s
    candidate sections for the worker's brief) rather than just the layout.
    """
    if template_version_id is None:
        return None, "patient", None, content, []
    structure = await repository_templates.structure_for_version(session, template_version_id)
    if not structure:
        return None, "patient", None, content, []
    sections = list(structure.get("sections") or [])
    blocks = structure.get("blocks")
    if not isinstance(blocks, list):
        blocks = [
            block
            for section in sections
            if isinstance(section, dict)
            for block in (section.get("blocks") or [])
            if isinstance(block, dict)
        ]
    presentation = structure.get("layout") or {}
    layout = (
        [dict(block) for block in blocks if isinstance(block, dict)] if isinstance(blocks, list) else None
    )
    persona = str(presentation.get("persona") or "patient")
    greeting = presentation.get("greeting")
    content = domain_content.content_for_template(content, sections)
    return layout, persona, (str(greeting) if greeting else None), content, sections


async def audience_sections(
    session: AsyncSession,
    template_version_id: uuid.UUID | None,
    content: dict[str, Any],
    audiences: tuple[str, ...],
    *,
    include_hidden: bool = False,
) -> list[AudienceSectionRead]:
    """A station's content, projected to what these audiences may read of it.

    `content` is the raw document (`station_versions.content`), not yet lifted
    onto block ids — this loads the template's structure and does that lifting
    itself, the same way `_presentation` does for the live render. A station
    bound to no template, or a template with no structure, has nothing to
    project and answers with no sections; a caller that still needs to serve
    something falls back to its own legacy reader.

    `audiences` is walked in the order given, each contributing its sections
    in template order — `("candidate", "examiner")` reads as the brief's
    sections followed by the review's, not interleaved by template position.
    """
    if template_version_id is None:
        return []
    structure = await repository_templates.structure_for_version(session, template_version_id)
    if not structure:
        return []
    sections = list(structure.get("sections") or [])
    lifted = domain_content.content_for_template(content, sections)
    # Keyed by section id: an examiner-role block filed in a candidate section
    # joins that section in the review rather than repeating its heading.
    by_id: dict[str, AudienceSectionRead] = {}
    for audience in audiences:
        projected = domain_audience.sections_for(sections, lifted, audience, include_hidden=include_hidden)
        for section in projected:
            blocks = [
                AudienceBlockRead(
                    id=block.id,
                    label=block.label,
                    type=block.type,
                    role=block.role,
                    value=block.value,
                    fields=[RecordFieldRead(**column) for column in block.fields] if block.fields else None,
                )
                for block in section.blocks
            ]
            existing = by_id.get(section.id)
            if existing is None:
                by_id[section.id] = AudienceSectionRead(
                    id=section.id, title=section.title, audience=section.audience, blocks=blocks
                )
            else:
                existing.blocks.extend(blocks)
    return list(by_id.values())


def candidate_brief_text(sections: list[domain_audience.AudienceSection]) -> str | None:
    """A `RunnableStation`'s candidate sections, rendered to the plain text the worker's
    `candidate_brief` contract carries — `None` for a station with no template."""
    return domain_audience.sections_as_text(sections) or None
