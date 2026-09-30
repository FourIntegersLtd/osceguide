"""Turning an authored rubric into the JSON Schema a marker is asked to fill.

The derivation is the point: the instructions an author typed become the property descriptions the
model reads, and the fields they defined become the properties it must fill, so the rubric and the
thing the model is constrained by cannot drift apart. The walk is over the rubric's own tree: each
domain, each competency in it, each field every competency answers, and each written section.

Two schemas come out of one walk:

- the *marker* schema (`derive_result_schema`): what the model is asked to fill;
- the *display* schema (`derive_display_schema`): the whole shape a stored result has, which adds
  the fields the platform writes itself (`source: system`).
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence
from typing import Any

from app.features.rubrics.structure import (
    NO_DEFAULT,
    CompetencySpec,
    FieldSpec,
    RatingSpec,
    RubricStructure,
    SectionSpec,
)

__all__ = ["derive_display_schema", "derive_result_schema", "framework_payload"]


def derive_result_schema(structure: RubricStructure) -> dict[str, Any]:
    """The JSON Schema a marker is asked to fill: the display schema without system fields."""
    return _derive(structure, include_system=False)


def derive_display_schema(structure: RubricStructure) -> dict[str, Any]:
    """The whole shape of a stored result, system-written fields included."""
    return _derive(structure, include_system=True)


def _derive(structure: RubricStructure, *, include_system: bool) -> dict[str, Any]:
    """One object per section, in authored order, plus the rubric's own instructions."""
    builder = _Builder(structure.rating, include_system)
    properties: dict[str, Any] = {}
    required: list[str] = []
    for section in structure.sections:
        if section.kind == "field":
            # A lone field sits at the top of the result under its own id.
            for lone_field in builder.visible(section.fields):
                properties[lone_field.id] = builder.field_property(lone_field)
                if lone_field.required:
                    required.append(lone_field.id)
            continue
        properties[section.id] = builder.section_property(section)
        if section.required:
            required.append(section.id)
    schema: dict[str, Any] = {"type": "object"}
    if structure.instructions:
        schema["description"] = structure.instructions
    schema.update({"additionalProperties": False, "required": required, "properties": properties})
    return schema


class _Builder:
    """The walk over one rubric, carrying its rating and whether system fields are shown."""

    def __init__(self, rating: RatingSpec, include_system: bool) -> None:
        """Remember what every field in this walk is built against."""
        self.rating = rating
        self.include_system = include_system

    def visible(self, fields: Sequence[FieldSpec]) -> list[FieldSpec]:
        """The fields this schema carries: all of them for display, marker-written ones for the marker."""
        return [spec for spec in fields if self.include_system or spec.source != "system"]

    def section_property(self, section: SectionSpec) -> dict[str, Any]:
        """A domain (its competencies, then its own fields) or a written section (its fields)."""
        properties: dict[str, Any] = {}
        required: list[str] = []
        for competency in section.competencies:
            properties[competency.id] = self.competency_property(competency, section.competency_fields)
            required.append(competency.id)
        for section_field in self.visible(section.fields):
            properties[section_field.id] = self.field_property(section_field)
            if section_field.required:
                required.append(section_field.id)
        body = _object(section.title, section.instructions, properties, required)
        if not section.nullable:
            return body
        # The way pydantic writes `X | None = None`: the wrapper carries its own
        # title and description beside the object's.
        wrapped: dict[str, Any] = {"anyOf": [body, {"type": "null"}], "default": None, "title": section.title}
        if section.description:
            wrapped["description"] = section.description
        return wrapped

    def competency_property(
        self, competency: CompetencySpec, competency_fields: Sequence[FieldSpec]
    ) -> dict[str, Any]:
        """One competency: an object answering every field its domain asks of each competency."""
        fields = self.visible(competency_fields)
        properties = {spec.id: self.field_property(spec) for spec in fields}
        required = [spec.id for spec in fields if spec.required]
        return _object(
            competency.label, competency_description(competency, self.rating), properties, required
        )

    def field_property(self, spec: FieldSpec) -> dict[str, Any]:
        """One field, by its answer format, with its instructions as the description."""
        core = self.field_core(spec)
        if spec.example is not None:
            core["example"] = spec.example
        decoration: dict[str, Any] = {}
        if spec.label:
            decoration["title"] = spec.label
        if spec.instructions:
            decoration["description"] = spec.instructions
        if spec.nullable:
            wrapped: dict[str, Any] = {"anyOf": [core, {"type": "null"}], **decoration}
            wrapped["default"] = None if spec.default is NO_DEFAULT else spec.default
            return wrapped
        if spec.default is not NO_DEFAULT:
            core["default"] = spec.default
        return {**core, **decoration}

    def field_core(self, spec: FieldSpec) -> dict[str, Any]:
        """The type-specific part of a field's schema."""
        if spec.type == "rating":
            return _rating_property(self.rating)
        if spec.type in ("shortText", "longText"):
            return {"type": "string"}
        if spec.type == "singleSelect":
            return {"type": "string", "enum": list(spec.options)}
        if spec.type in ("group", "records"):
            children = self.visible(spec.fields)
            properties = {child.id: self.field_property(child) for child in children}
            required = [child.id for child in children if child.required]
            body: dict[str, Any] = {"type": "object", "additionalProperties": False}
            if required:
                body["required"] = required
            body["properties"] = properties
            return body if spec.type == "group" else _array(body, spec.min_items)
        return _array({"type": "string"}, spec.min_items)


def competency_description(competency: CompetencySpec, rating: RatingSpec) -> str:
    """What the model reads for a competency: label, then anchors, then instructions.

    Each part is left out when the instructions already say it, so a rubric
    whose instructions are a legacy description verbatim (anchors included)
    reads exactly as that description did, and one with only a label and
    anchors reads as version 1 did: the label, then "G: ..." per value in the
    rating's own order.
    """
    instructions = competency.instructions.strip()
    flattened_instructions = _flatten(instructions)
    ordered = [value for value in rating.scale if value in competency.descriptors]
    ordered += [value for value in competency.descriptors if value not in ordered]
    anchors = [
        f"{value}: {competency.descriptors[value]}"
        for value in ordered
        if _flatten(competency.descriptors[value]) not in flattened_instructions
    ]
    parts = [] if instructions else [competency.label]
    parts += anchors
    if instructions:
        parts.append(competency.instructions)
    return "\n".join(part for part in parts if part)


def _flatten(text: str) -> str:
    """Text with every run of whitespace as one space, so a wrapped anchor still matches."""
    return re.sub(r"\s+", " ", text).strip()


def _object(label: str, description: str, properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    """A closed object schema with its title and, when there is one, its description."""
    body: dict[str, Any] = {"type": "object", "title": label}
    if description:
        body["description"] = description
    body["additionalProperties"] = False
    # Left out when nothing is required, the way pydantic writes an object of
    # optional fields (CASC's competencies).
    if required:
        body["required"] = required
    body["properties"] = properties
    return body


def _array(items: dict[str, Any], min_items: int | None) -> dict[str, Any]:
    """An array of `items`, with its minimum length when the author set one."""
    array: dict[str, Any] = {"type": "array", "items": items}
    if min_items is not None:
        array["minItems"] = min_items
    return array


def _rating_property(rating: RatingSpec) -> dict[str, Any]:
    """A rating in the rubric's native units: a listed value, a bounded number, or true/false."""
    if rating.is_enumerated:
        return {"type": "string", "enum": list(rating.scale)}
    if rating.kind == "boolean":
        return {"type": "boolean"}
    number: dict[str, Any] = {"type": "integer" if rating.step == "integer" else "number"}
    if rating.maximum is not None:
        number["maximum"] = rating.maximum
    if rating.minimum is not None:
        number["minimum"] = rating.minimum
    return number


def framework_payload(
    *,
    framework_id: str,
    label: str,
    version: str,
    structure: RubricStructure,
    system_prompt: str,
) -> dict[str, Any]:
    """The rubric as `osce_assessment.CompetencyFramework` serialises.

    A plain dict, built here rather than by importing the engine's model, so
    this slice (and everything that stores this payload) stays free of the
    engine. The engine validates it on the way in and forbids unknown keys, so
    this sends exactly the keys the engine declares: the native `rating`, the
    competency field that holds it (`rating_field`), each domain's `nullable`
    and every field's role (`field_roles`), which is what lets the engine
    check a mark natively and the debrief tutor read a result by role.

    `scale` is sent only for an enumerated rating; left out, the engine keeps
    its default. Descriptors go with it, since the engine checks each against
    the scale. A competency keeps its own id, which the live coverage panel
    and its detector key on, unless another domain uses the same name (Ortho
    does): the framework needs ids unique, so only those are qualified
    `domain.competency`. The result still nests each under its domain by
    local name.
    """
    rating = structure.rating
    name_counts = Counter(competency.id for domain in structure.domains for competency in domain.competencies)
    payload: dict[str, Any] = {"id": framework_id, "label": label, "version": version}
    if structure.scale:
        payload["scale"] = list(structure.scale)
    payload["rating"] = {
        "kind": rating.kind,
        "minimum": rating.minimum,
        "maximum": rating.maximum,
        "step": rating.step,
    }
    payload["rating_field"] = rating.field
    payload["domains"] = [
        {"id": domain.id, "label": domain.title, "live": domain.live, "nullable": domain.nullable}
        for domain in structure.domains
    ]
    payload["competencies"] = [
        {
            "id": competency.id if name_counts[competency.id] == 1 else f"{domain.id}.{competency.id}",
            "label": competency.label,
            "domain_id": domain.id,
            "descriptors": dict(competency.descriptors) if structure.scale else {},
        }
        for domain in structure.domains
        for competency in domain.competencies
    ]
    payload["field_roles"] = field_roles(structure)
    payload["result_schema"] = derive_result_schema(structure)
    payload["system_prompt"] = system_prompt
    return payload


def field_roles(structure: RubricStructure) -> dict[str, str]:
    """Every field id in the result mapped to its role, for readers that walk a result by role.

    The engine keys roles by field id alone, so where two fields share an id
    the first one in the rubric's order wins; the rating field is always
    `rating`. A group's own fields are included, since the tutor reads inside
    groups too.
    """
    roles: dict[str, str] = {structure.rating.field: "rating"}

    def add(fields: Sequence[FieldSpec]) -> None:
        """Record each field's role (first one wins), then its group's fields."""
        for spec in fields:
            roles.setdefault(spec.id, spec.role)
            add(spec.fields)

    for section in structure.sections:
        add(section.competency_fields)
        add(section.fields)
    return roles
