"""What a rubric is, and the JSON Schema a marker is asked to fill.

A rubric is the thing a candidate is marked against: a scale, some domains, the competencies in each,
and what earns each point of the scale on each competency, plus the free-shape sections a result
carries that nobody scores, like narrative feedback. It is one row an admin writes, and the schema
is *derived* from it, so the descriptors the author typed are the descriptors the model reads.

`result_schema_override` remains for a shape this derivation cannot express. It is an escape hatch,
not the normal path: a rubric that uses it can still be marked but its competencies no longer
describe its own result.

Pure: no session, no models, no I/O.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from app.features.rubrics.schema_builder import (
    derive_result_schema,
    framework_payload,
    result_schema_for,
)
from app.features.rubrics.structure import (
    CompetencySpec,
    DomainSpec,
    InvalidRubric,
    RubricStructure,
    SectionSpec,
)

__all__ = [
    "NON_SCORING_SECTIONS",
    "CompetencySpec",
    "DomainSpec",
    "InvalidRubric",
    "RubricStructure",
    "SectionSpec",
    "derive_result_schema",
    "framework_payload",
    "narrow_structure",
    "parse_structure",
    "result_schema_for",
    "reviewable_domains",
    "scoring_domain_ids",
    "validate_pacing",
]

# An id is used as a JSON property name and read back by code, so it is
# constrained the way an identifier is rather than left as free text.
_ID = re.compile(r"^[a-z][a-z0-9_]{0,63}$")

_SECTION_KINDS = ("text", "list", "object")

# What a marker writes that nobody scores: narrative, not a rating. A reviewer
# is not asked to agree or disagree with these, so they never count towards a
# complete review (R-1), and narrowing a rubric never drops them.
NON_SCORING_SECTIONS = frozenset({"actionable_feedback", "clinical_analysis", "overall_priorities"})


def parse_structure(raw: Mapping[str, Any] | None) -> RubricStructure:
    """Read a stored structure, refusing anything that could not be marked.

    Everything here is checked at the boundary rather than trusted, because a
    structure arrives as JSON from an API and is later turned into the schema a
    model is constrained by. A duplicate id would silently drop a competency
    from the result; a descriptor for a score that is not on the scale would be
    an instruction the model cannot follow.
    """
    data = raw or {}
    if not isinstance(data, Mapping):
        raise InvalidRubric("A rubric structure must be an object.")

    scale = tuple(str(value) for value in data.get("scale") or ())
    if not scale:
        raise InvalidRubric("A rubric needs a scale: the scores a competency may be given.")
    if len(set(scale)) != len(scale):
        raise InvalidRubric(f"The scale repeats a value: {sorted(scale)}.")

    domains: list[DomainSpec] = []
    seen_ids: set[str] = set()
    seen_competencies: set[str] = set()

    for raw_domain in data.get("domains") or ():
        domain_id = _identifier(raw_domain, "domain")
        if domain_id in seen_ids:
            raise InvalidRubric(f"Two domains are called {domain_id!r}.")
        seen_ids.add(domain_id)

        competencies: list[CompetencySpec] = []
        for raw_competency in raw_domain.get("competencies") or ():
            competency_id = _identifier(raw_competency, "competency")
            if competency_id in seen_competencies:
                raise InvalidRubric(f"Two competencies are called {competency_id!r}.")
            seen_competencies.add(competency_id)
            descriptors = {str(k): str(v) for k, v in (raw_competency.get("descriptors") or {}).items()}
            off_scale = sorted(set(descriptors) - set(scale))
            if off_scale:
                raise InvalidRubric(
                    f"Competency {competency_id!r} describes {off_scale}, "
                    f"which are not on the scale {list(scale)}."
                )
            competencies.append(
                CompetencySpec(
                    id=competency_id,
                    label=str(raw_competency.get("label") or competency_id),
                    descriptors=descriptors,
                )
            )
        domains.append(
            DomainSpec(
                id=domain_id,
                label=str(raw_domain.get("label") or domain_id),
                live=bool(raw_domain.get("live", False)),
                competencies=tuple(competencies),
            )
        )

    sections: list[SectionSpec] = []
    for raw_section in data.get("sections") or ():
        section_id = _identifier(raw_section, "section")
        if section_id in seen_ids:
            raise InvalidRubric(f"{section_id!r} is both a domain and a section.")
        seen_ids.add(section_id)
        kind = str(raw_section.get("kind") or "text")
        if kind not in _SECTION_KINDS:
            raise InvalidRubric(
                f"Section {section_id!r} is a {kind!r}; expected one of {list(_SECTION_KINDS)}."
            )
        schema = raw_section.get("schema")
        if kind == "object" and not isinstance(schema, Mapping):
            raise InvalidRubric(f"Section {section_id!r} is an object and needs a schema describing it.")
        sections.append(
            SectionSpec(
                id=section_id,
                label=str(raw_section.get("label") or section_id),
                kind=kind,
                schema=dict(schema) if isinstance(schema, Mapping) else None,
            )
        )

    if not domains and not sections:
        raise InvalidRubric("A rubric with no domains and no sections asks the marker for nothing.")
    return RubricStructure(scale=scale, domains=tuple(domains), sections=tuple(sections))


def _identifier(raw: Any, what: str) -> str:
    if not isinstance(raw, Mapping):
        raise InvalidRubric(f"Each {what} must be an object.")
    value = str(raw.get("id") or "").strip()
    if not _ID.match(value):
        raise InvalidRubric(
            f"{value!r} is not a usable {what} id: lower-case letters, digits and "
            "underscores, starting with a letter."
        )
    return value


def validate_pacing(raw: Mapping[str, Any] | None) -> dict[str, int]:
    """The consultation clock stored with a rubric, checked before it is saved.

    The same four marks the engine renders phase budgets from. They are checked
    here as well as there because a clock that cannot be run is a rubric that
    cannot be used, and the author should hear about it at the moment they
    write it rather than when a candidate starts a station.
    """
    data = raw or {}
    try:
        pacing = {
            key: int(data[key])
            for key in ("total_seconds", "history_seconds", "introduction_seconds", "safety_net_seconds")
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidRubric(
            "Pacing needs four whole numbers of seconds: total_seconds, history_seconds, "
            f"introduction_seconds, safety_net_seconds ({exc})."
        ) from exc
    if pacing["total_seconds"] <= 0:
        raise InvalidRubric("A consultation with no time cannot be run.")
    if not 0 < pacing["introduction_seconds"] < pacing["history_seconds"]:
        raise InvalidRubric("The introduction must end before history taking does.")
    safety_net_starts_at = pacing["total_seconds"] - pacing["safety_net_seconds"]
    if not pacing["history_seconds"] < safety_net_starts_at < pacing["total_seconds"]:
        raise InvalidRubric("Safety netting must start after history taking and before the end.")
    return pacing


def reviewable_domains(field_selection: Mapping[str, Any] | None) -> frozenset[str]:
    """Which domains a feedback template asks reviewers to score.

    A template's `field_selection` names either its `domains` outright or the
    `paths` it keeps from the rubric's schema, where the first segment of a
    path is its domain. Both forms are accepted so a selection copied from the
    legacy import and one authored here read the same.
    """
    selection = field_selection or {}
    names: set[str] = set()
    for domain_name in selection.get("domains") or []:
        names.add(str(domain_name))
    for path in selection.get("paths") or []:
        head = str(path).split(".", 1)[0].strip()
        if head:
            names.add(head)
    return frozenset(names - NON_SCORING_SECTIONS)


def narrow_structure(
    structure: RubricStructure, field_selection: Mapping[str, Any] | None
) -> RubricStructure:
    """The rubric as a feedback template asks for it.

    A template selects the domains its reviewers work through; the non-scoring
    sections are always kept, because they are what the candidate reads. An
    empty selection means the whole rubric, which is what an org that has not
    narrowed anything wants.
    """
    wanted = reviewable_domains(field_selection)
    if not wanted:
        return structure
    unknown = sorted(wanted - {d.id for d in structure.domains})
    if unknown:
        raise InvalidRubric(f"The selection names {unknown}, which this rubric does not define.")
    return RubricStructure(
        scale=structure.scale,
        domains=tuple(d for d in structure.domains if d.id in wanted),
        sections=structure.sections,
    )


def scoring_domain_ids(structure: RubricStructure) -> frozenset[str]:
    """Domains a human review must score when using the full rubric."""
    return frozenset(d.id for d in structure.domains if d.id not in NON_SCORING_SECTIONS)
