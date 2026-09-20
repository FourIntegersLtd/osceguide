"""Mapping a rubric row onto the schema the routes return."""

from __future__ import annotations

from typing import Any

from app.features.rubrics import domain, errors
from app.features.rubrics.models import Rubric, RubricVersion
from app.features.rubrics.schemas import RubricRead, RubricVersionRead


def validated(
    structure: dict[str, Any], pacing: dict[str, Any]
) -> tuple[domain.RubricStructure, dict[str, int]]:
    try:
        return domain.parse_structure(structure), domain.validate_pacing(pacing)
    except domain.InvalidRubric as exc:
        raise errors.InvalidRubricError(str(exc)) from exc


def validate_marking_layout(marking_layout: dict[str, Any] | None) -> None:
    if marking_layout is None:
        return
    if not isinstance(marking_layout, dict) or not marking_layout.get("sections"):
        raise errors.InvalidRubricError("A marking layout must include sections.")


def rubric_read(rubric: Rubric, versions: list[RubricVersion]) -> RubricRead:
    return RubricRead(
        id=rubric.id,
        owner_kind=rubric.owner_kind,
        org_id=rubric.org_id,
        title=rubric.title,
        current_version_id=rubric.current_version_id,
        versions=[version_read(v) for v in versions],
    )


def version_read(version: RubricVersion) -> RubricVersionRead:
    try:
        schema = domain.result_schema_for(
            domain.parse_structure(version.structure), version.result_schema_override
        )
    except domain.InvalidRubric:
        # A draft may be half-written. Showing an empty schema is better than
        # refusing to show the draft its author is in the middle of writing.
        schema = {}
    return RubricVersionRead(
        id=version.id,
        rubric_id=version.rubric_id,
        version=version.version,
        status=version.status,
        structure=dict(version.structure or {}),
        system_prompt=version.system_prompt,
        pacing=dict(version.pacing or {}),
        result_schema=schema,
        marking_layout=dict(version.marking_layout) if version.marking_layout else None,
        published_at=version.published_at,
    )
