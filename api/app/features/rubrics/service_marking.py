"""Handing a rubric to whatever is about to mark with it.

`marking_snapshot` is the outward-facing one: it returns the rubric as the
engine wants it — a framework, its prompt, its clock — so the caller can freeze
that onto an attempt and mark it later without reading a row that may since
have changed. Re-marking an attempt a year from now then uses the wording it
was assessed against rather than whatever the rubric says today.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import lifecycle
from app.core.schemas import (
    DomainTotalRead,
    RatingRead,
    ResultTotalsRead,
    ReviewFieldRead,
    ReviewFormRead,
)
from app.features.rubrics import domain, errors, repository
from app.features.rubrics import service_scoring as scoring
from app.features.rubrics.models import RubricVersion


async def published_version(
    session: AsyncSession, org_id: uuid.UUID | None, version_id: uuid.UUID
) -> RubricVersion:
    """A published rubric version this owner may use, or a refusal saying why."""
    version_row = await repository.version_by_id(session, org_id, version_id)
    if version_row is None:
        raise errors.RubricVersionNotFound()
    if version_row.status != lifecycle.Status.PUBLISHED:
        raise errors.RubricVersionNotPublished()
    return version_row


async def published_platform_version(session: AsyncSession, version_id: uuid.UUID) -> RubricVersion:
    """What an exam may be marked with: published, and owned by the platform."""
    version_row = await repository.published_platform_version(session, version_id)
    if version_row is None:
        raise errors.RubricVersionNotFound("An exam must name a published rubric version the platform owns.")
    return version_row


async def marking_snapshot(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    *,
    rubric_version_id: uuid.UUID,
    field_selection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The rubric as the engine needs it, ready to be frozen onto an attempt.

    Frozen rather than looked up at marking time so that re-marking an attempt
    a year later uses the wording it was assessed against, not whatever the
    rubric says now. `field_selection` narrows it to the domains a feedback
    template asks for.
    """
    version = await published_version(session, org_id, rubric_version_id)
    rubric = await repository.readable_rubric(session, org_id, version.rubric_id)
    return _snapshot_of(version, rubric.title if rubric else "Rubric", field_selection)


async def trial_rubric(
    session: AsyncSession, org_id: uuid.UUID | None, rubric_id: uuid.UUID, version: int
) -> tuple[dict[str, Any], ScoringRubric]:
    """One of this owner's own versions, at any status, as a trial mark would use it (plan §8).

    The same snapshot an attempt freezes, so a trial marks exactly as a real
    attempt would once the version is published; and the scoring rubric its
    result is totalled by. A draft is allowed, which is the point of a trial,
    but it must be one publishing would accept, or the marker has no schema.
    """
    rubric = await repository.rubric_by_id(session, org_id, rubric_id)
    if rubric is None:
        raise errors.RubricNotFound()
    version_row = await repository.version_by_number(session, org_id, rubric_id, version)
    if version_row is None:
        raise errors.RubricVersionNotFound()
    try:
        domain.parse_structure(version_row.structure)
    except domain.InvalidRubric as exc:
        raise errors.InvalidRubricError(str(exc), details={"errors": domain.validation_errors(exc)}) from exc
    if not (version_row.system_prompt or "").strip():
        raise errors.InvalidRubricError("A rubric cannot mark without marking instructions.")
    snapshot = _snapshot_of(version_row, rubric.title, None)
    scoring = frozen_scoring_rubric(snapshot)
    if scoring is None:  # _snapshot_of always freezes a structure; this only narrows the type
        raise errors.InvalidRubricError("This rubric version has no structure to mark with.")
    return snapshot, scoring


def _snapshot_of(
    version: RubricVersion, title: str, field_selection: dict[str, Any] | None
) -> dict[str, Any]:
    """A version as the engine needs it: what `marking_snapshot` freezes and a trial marks with."""
    structure = domain.narrow_structure(domain.parse_structure(version.structure), field_selection)
    layout = dict(version.marking_layout) if version.marking_layout else None
    return {
        # The rubric itself (version 2, narrowed like the framework) and how it
        # is read, so the attempt is scored and shown by its own rules forever.
        "structure": domain.frozen_structure(version.structure, field_selection),
        "display": domain.resolved_display(structure),
        "framework": domain.framework_payload(
            framework_id=str(version.id),
            label=title,
            version=str(version.version),
            structure=structure,
            system_prompt=version.system_prompt,
        ),
        # What the marker reads: the author's instructions plus the feedback tone they picked.
        "system_prompt": domain.prompt_with_tone(version.system_prompt, structure.display.feedback_tone),
        "pacing": dict(version.pacing or {}),
        "marking_layout": layout,
    }


def reviewable_domains(field_selection: dict[str, Any] | None) -> set[str]:
    """Which domains a feedback template asks reviewers to score.

    Pure, but exposed on the service because it is the door other slices use:
    `reviews` needs to know what a complete review is, and `sittings` needs to
    know what it is binding.
    """
    return set(domain.reviewable_domains(field_selection))


# --- Scoring an attempt by the rubric it was marked with -------------------------


@dataclass(frozen=True)
class ScoringRubric:
    """The rubric an attempt is scored and shown by: parsed, raw (version 2) and its display."""

    structure: domain.RubricStructure
    # The same structure as JSON, version 2, for a screen to draw feedback from.
    raw_structure: dict[str, Any]
    # `domain.resolved_display`: every gap filled.
    display: dict[str, Any]
    # The rubric version it came from, when known; tells a dashboard whether
    # attempts were scored under different versions.
    version_id: str | None


def frozen_scoring_rubric(snapshot: Mapping[str, Any] | None) -> ScoringRubric | None:
    """The scoring rubric frozen onto an attempt, or None if it predates freezing one.

    A snapshot carries `structure` and `display` beside the framework. The
    oldest attempts carry only the framework, and get None here.
    """
    if not isinstance(snapshot, Mapping) or not isinstance(snapshot.get("structure"), Mapping):
        return None
    raw_structure = dict(snapshot["structure"])
    structure = domain.parse_structure(raw_structure)
    frozen_display = snapshot.get("display")
    display = (
        dict(frozen_display) if isinstance(frozen_display, Mapping) else domain.resolved_display(structure)
    )
    return ScoringRubric(
        structure=structure,
        raw_structure=domain.upgrade_structure(raw_structure),
        display=display,
        version_id=_framework_version_id(snapshot),
    )


async def scoring_rubric(
    session: AsyncSession,
    snapshot: Mapping[str, Any] | None,
    *,
    exam_rubric_version_id: uuid.UUID | None,
) -> ScoringRubric | None:
    """The rubric an attempt is scored by, or None if nothing can score it.

    In order:

    1. the structure and display frozen on the attempt;
    2. an attempt frozen before those were: the rubric version its framework
       names (the framework id is the version id), narrowed to the domains the
       framework kept;
    3. an attempt with no frozen rubric at all (imported `legacy-b2c` rows):
       the first version 2 version of its exam's platform rubric, which the
       exact-match contract test proves has the legacy result's shape.
    """
    frozen = frozen_scoring_rubric(snapshot)
    if frozen is not None:
        return frozen
    framework_version_id = _framework_version_id(snapshot)
    if framework_version_id is not None:
        version = await repository.version_by_id_for_scoring(session, uuid.UUID(framework_version_id))
        if version is not None:
            return _scoring_from_version(version, _framework_domain_ids(snapshot))
    if exam_rubric_version_id is None:
        return None
    exam_version = await repository.version_by_id_for_scoring(session, exam_rubric_version_id)
    if exam_version is None:
        return None
    first_v2 = await repository.first_v2_platform_version(session, exam_version.rubric_id)
    return _scoring_from_version(first_v2 or exam_version, None)


def _scoring_from_version(version: RubricVersion, domain_ids: list[str] | None) -> ScoringRubric:
    """A scoring rubric read from a stored version, narrowed to `domain_ids` when given."""
    selection = {"domains": domain_ids} if domain_ids else None
    raw_structure = domain.frozen_structure(version.structure, selection)
    structure = domain.parse_structure(raw_structure)
    return ScoringRubric(
        structure=structure,
        raw_structure=raw_structure,
        display=domain.resolved_display(structure),
        version_id=str(version.id),
    )


def _framework_version_id(snapshot: Mapping[str, Any] | None) -> str | None:
    """The rubric version id a frozen framework was built from, if it is one."""
    framework = snapshot.get("framework") if isinstance(snapshot, Mapping) else None
    framework_id = framework.get("id") if isinstance(framework, Mapping) else None
    try:
        return str(uuid.UUID(str(framework_id))) if framework_id else None
    except ValueError:
        return None


def _framework_domain_ids(snapshot: Mapping[str, Any] | None) -> list[str] | None:
    """The domains a frozen framework kept (it may have been narrowed), or None."""
    framework = snapshot.get("framework") if isinstance(snapshot, Mapping) else None
    domains = framework.get("domains") if isinstance(framework, Mapping) else None
    if not isinstance(domains, list):
        return None
    return [str(entry["id"]) for entry in domains if isinstance(entry, Mapping) and entry.get("id")]


def engine_framework(scoring_rubric: ScoringRubric) -> dict[str, Any]:
    """The scoring rubric as the engine's `CompetencyFramework` payload.

    Built from the structure rather than read from the snapshot's frozen
    framework, because the oldest frozen frameworks lack the rating and
    the field roles the engine's by-role renderer needs; the structure is the
    source of truth for both. Used by the debrief tutor's `render_marking`.
    """
    return domain.framework_payload(
        framework_id=scoring_rubric.version_id or "rubric",
        label="Marking rubric",
        version="1",
        structure=scoring_rubric.structure,
        system_prompt="",
    )


async def scoring_rubric_for_version(
    session: AsyncSession, org_id: uuid.UUID | None, version_id: uuid.UUID
) -> ScoringRubric:
    """A published version as a scoring rubric: what a sitting's reviews are checked and scored by."""
    return _scoring_from_version(await published_version(session, org_id, version_id), None)


def rating_read(structure: domain.RubricStructure) -> RatingRead:
    """A rubric's rating as the routes return it."""
    rating = structure.rating
    return RatingRead(
        kind=rating.kind,
        field=rating.field,
        scale=list(structure.scale),
        minimum=rating.minimum,
        maximum=rating.maximum,
        step=rating.step,
        points=list(rating.points) if rating.points else None,
    )


def review_form(scoring_rubric: ScoringRubric) -> ReviewFormRead:
    """Every rating a reviewer may set on a slot marked by this rubric (plan §7, the review forms).

    Each scoring domain offers a whole-domain rating and one per competency,
    both saved under paths ending in the rubric's rating field, which is what
    `reviews` validates and scores.
    """
    structure = scoring_rubric.structure
    rating_field = structure.rating.field
    scoring_domains = domain.scoring_domain_ids(structure)
    fields: list[ReviewFieldRead] = []
    for section in structure.domains:
        if section.id not in scoring_domains:
            continue
        fields.append(
            ReviewFieldRead(
                path=f"{section.id}.{rating_field}",
                domain_id=section.id,
                domain_label=section.title,
                label=section.title,
            )
        )
        fields.extend(
            ReviewFieldRead(
                path=f"{section.id}.{competency.id}.{rating_field}",
                domain_id=section.id,
                domain_label=section.title,
                competency_id=competency.id,
                label=competency.label,
                descriptors=dict(competency.descriptors),
            )
            for competency in section.competencies
        )
    return ReviewFormRead(
        rubric_version_id=scoring_rubric.version_id,
        rating=rating_read(structure),
        fields=fields,
        required_domains=sorted(scoring_domains),
    )


def totals_read(scoring_rubric: ScoringRubric, result: Mapping[str, Any]) -> ResultTotalsRead:
    """One marked result's numbers, by the rubric it was marked with, as the routes return them."""
    totals = scoring.result_totals(scoring_rubric.structure, scoring_rubric.display, result)
    return ResultTotalsRead(
        total=totals.total,
        max=totals.maximum,
        fraction=totals.fraction,
        passed=totals.passed,
        critical_count=totals.critical_count,
        domains=[
            DomainTotalRead(
                id=domain_total.id,
                label=domain_total.label,
                value=domain_total.value,
                counts=dict(domain_total.counts),
                passed=domain_total.passed,
            )
            for domain_total in totals.domains
        ],
    )


async def scheme_structure(session: AsyncSession, version_id: uuid.UUID) -> dict[str, Any]:
    """A version's marking scheme in the author's form, for a screen that only displays it.

    Not org-scoped: the caller has already authorised the circuit whose sitting is bound to this
    version. Only `structure` leaves, never the marker's system prompt or pacing.
    """
    version = await repository.version_by_id_for_scoring(session, version_id)
    if version is None:
        raise errors.RubricVersionNotFound()
    return domain.authoring_form(version.structure)
