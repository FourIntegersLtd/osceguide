"""Turning an authored rubric into the JSON Schema a marker is asked to fill.

The derivation is the point: the descriptors an author typed become the property descriptions the
model reads, so the rubric and the thing the model is constrained by cannot drift apart.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from app.features.rubrics.structure import CompetencySpec, RubricStructure, SectionSpec

__all__ = ["derive_result_schema", "framework_payload", "result_schema_for"]


def derive_result_schema(structure: RubricStructure) -> dict[str, Any]:
    """The JSON Schema a marker is asked to fill, built from the rubric itself.

    One object per domain holding one object per competency — a score on the
    rubric's own scale, the phrase that evidences it, and the explanation —
    plus each section in the shape its author chose. The descriptors become the
    property description, which is where the model actually reads them.
    """
    properties: dict[str, Any] = {}
    for domain in structure.domains:
        properties[domain.id] = {
            "type": "object",
            "title": domain.label,
            "additionalProperties": False,
            "required": [competency.id for competency in domain.competencies],
            "properties": {
                competency.id: _scored_property(competency, structure.scale)
                for competency in domain.competencies
            },
        }
    for section in structure.sections:
        properties[section.id] = _section_property(section)
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(properties),
        "properties": properties,
    }


def _scored_property(competency: CompetencySpec, scale: Sequence[str]) -> dict[str, Any]:
    """The JSON Schema for one competency: a score plus the phrase and reasoning behind it."""
    described = "\n".join(
        f"{scale_value}: {competency.descriptors[scale_value]}"
        for scale_value in scale
        if scale_value in competency.descriptors
    )
    return {
        "type": "object",
        "title": competency.label,
        "description": f"{competency.label}\n{described}" if described else competency.label,
        "additionalProperties": False,
        "required": ["score", "supporting_phrase", "score_explanation"],
        "properties": {
            "score": {"type": "string", "enum": list(scale)},
            "supporting_phrase": {"type": "string"},
            "score_explanation": {"type": "string"},
        },
    }


def _section_property(section: SectionSpec) -> dict[str, Any]:
    """The JSON Schema for one written (non-scored) section, by its kind."""
    if section.kind == "list":
        return {"type": "array", "title": section.label, "items": {"type": "string"}}
    if section.kind == "object":
        return {**dict(section.schema or {}), "title": section.label}
    return {"type": "string", "title": section.label}


def result_schema_for(
    structure: RubricStructure, override: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """The derived schema, unless the author supplied one outright."""
    if override:
        return dict(override)
    return derive_result_schema(structure)


def framework_payload(
    *,
    framework_id: str,
    label: str,
    version: str,
    structure: RubricStructure,
    system_prompt: str,
    override: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """The rubric as `osce_assessment.CompetencyFramework` serialises.

    A plain dict, built here rather than by importing the engine's model, so
    this slice — and everything that stores this payload — stays free of the
    engine. The engine validates it on the way in.
    """
    return {
        "id": framework_id,
        "label": label,
        "version": version,
        "scale": list(structure.scale),
        "domains": [
            {"id": domain.id, "label": domain.label, "live": domain.live} for domain in structure.domains
        ],
        "competencies": [
            {
                "id": competency.id,
                "label": competency.label,
                "domain_id": domain.id,
                "descriptors": dict(competency.descriptors),
            }
            for domain in structure.domains
            for competency in domain.competencies
        ],
        "result_schema": result_schema_for(structure, override),
        "system_prompt": system_prompt,
    }
