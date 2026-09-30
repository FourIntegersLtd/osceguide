"""What a rubric is, and the JSON Schema a marker is asked to fill.

A rubric is the thing a candidate is marked against: how a competency is rated,
the domains and the competencies in each, what every competency answers, the
written sections nobody rates, and how feedback and the dashboard read the
result. It is one row an admin writes, and the schema is *derived* from it, so
the instructions the author typed are the instructions the model reads.

Stored structures come in two versions. Version 1 (a scale, domains and
sections, every competency answering a score, a phrase and an explanation) is
upgraded to version 2 on every read by `upgrade_structure`, so existing org
rubrics and frozen attempts keep working with no data migration.

Pure: no session, no models, no I/O.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from app.features.rubrics import validation
from app.features.rubrics.legacy_model import field_from_schema
from app.features.rubrics.schema_builder import (
    derive_display_schema,
    derive_result_schema,
    framework_payload,
)
from app.features.rubrics.structure import (
    NO_DEFAULT,
    CompetencySpec,
    DisplayBand,
    DisplayDomain,
    DisplaySpec,
    DisplayTone,
    DisplayTotal,
    FieldSpec,
    InvalidRubric,
    RatingSpec,
    RubricStructure,
    SectionSpec,
)

__all__ = [
    "NON_SCORING_SECTIONS",
    "CompetencySpec",
    "FieldSpec",
    "InvalidRubric",
    "RatingSpec",
    "RubricStructure",
    "SectionSpec",
    "derive_display_schema",
    "derive_result_schema",
    "framework_payload",
    "frozen_structure",
    "narrow_structure",
    "parse_structure",
    "resolved_display",
    "reviewable_domains",
    "scoring_domain_ids",
    "upgrade_structure",
    "validate_pacing",
]

# What a marker writes that nobody scores: narrative, not a rating. A reviewer
# is not asked to agree or disagree with these, so they never count towards a
# complete review (R-1), and narrowing a rubric never drops them.
NON_SCORING_SECTIONS = frozenset({"actionable_feedback", "clinical_analysis", "overall_priorities"})

# What every version 1 competency answered, in the order v1 derived it.
_V1_COMPETENCY_FIELDS: tuple[dict[str, Any], ...] = (
    {"id": "score", "type": "rating", "role": "rating"},
    {"id": "supporting_phrase", "type": "longText", "role": "evidence"},
    {"id": "score_explanation", "type": "longText", "role": "explanation"},
)
_V1_SECTION_KINDS = ("text", "list", "object")


class _RubricRefused(InvalidRubric):
    """An `InvalidRubric` carrying every validation error, not just the first."""

    def __init__(self, errors: list[validation.ValidationError]) -> None:
        """Say the first problem, and keep the rest for the API's error list."""
        first = errors[0]
        where = f" (at {first['path']})" if first["path"] else ""
        more = f" {len(errors) - 1} more problem(s) listed." if len(errors) > 1 else ""
        super().__init__(f"{first['message']}{where}{more}")
        self.errors = errors


def validation_errors(exc: InvalidRubric) -> list[validation.ValidationError]:
    """Every problem an `InvalidRubric` stands for, as `{path, message}` items."""
    if isinstance(exc, _RubricRefused):
        return list(exc.errors)
    return [{"path": "", "message": str(exc)}]


def parse_structure(raw: Mapping[str, Any] | None) -> RubricStructure:
    """Read a stored structure, refusing anything that could not be marked.

    A version 1 structure is upgraded first, so both read through one path.
    Every rule in `validation.py` is checked at this boundary rather than
    trusted, because a structure arrives as JSON from an API and is later
    turned into the schema a model is constrained by: a duplicate id would
    silently drop a competency, a descriptor for a rating the rubric does not
    have would be an instruction the model cannot follow.
    """
    if raw is not None and not isinstance(raw, Mapping):
        raise InvalidRubric("A rubric structure must be an object.")
    structure = upgrade_structure(raw or {})
    errors = validation.validate_structure(structure)
    if errors:
        raise _RubricRefused(errors)
    rating = _rating(structure["rating"])
    parsed = RubricStructure(
        rating=rating,
        sections=tuple(_section(raw_section) for raw_section in structure["sections"]),
        display=_display(structure.get("display")),
        instructions=_text(structure.get("instructions")),
    )
    unreachable = _pass_lines_out_of_reach(resolved_display(parsed))
    if unreachable:
        raise _RubricRefused(unreachable)
    return parsed


def _pass_lines_out_of_reach(display: Mapping[str, Any]) -> list[validation.ValidationError]:
    """Pass lines no candidate could reach, judged against the resolved maxima.

    `validation.py` checks a pass line against a maximum the author typed.
    Most rubrics leave the maximum to be derived (Ortho's 50 is 10 per
    competency times the competencies a result answers), so only once the
    display is resolved can a pass line of 60 be seen to be impossible.
    """
    problems: list[validation.ValidationError] = []
    for part in ("domain", "total"):
        maximum, pass_line = display[part]["max"], display[part]["passAtLeast"]
        if maximum is not None and pass_line is not None and pass_line > maximum:
            problems.append(
                {
                    "path": f"display.{part}.passAtLeast",
                    "message": f"The pass line ({pass_line:g}) is more than a candidate "
                    f"can score ({maximum:g}).",
                }
            )
    return problems


# --- Version 1 -> version 2 ------------------------------------------------------


def upgrade_structure(raw: Mapping[str, Any]) -> dict[str, Any]:
    """A stored structure in the version 2 shape, converting a version 1 one.

    Version 1 fixed what every competency answered: a score on the scale, the
    supporting phrase and the explanation. Those become each domain's
    competency fields exactly as v1 derived them, so a v1 rubric and every
    attempt frozen against one mark and read the same as before. A scale of R,
    A and G becomes an R/A/G rating, written best first; any other scale stays
    a scale in its own order. A v1 section was always one required top-level
    field: a list or text becomes that field, and an object becomes a `group`
    read from its schema.
    """
    if raw.get("schemaVersion") == validation.SCHEMA_VERSION:
        return dict(raw)
    scale = [str(value) for value in raw.get("scale") or ()]
    if not scale:
        raise InvalidRubric("A rubric needs a scale: the scores a competency may be given.")
    rating: dict[str, Any] = (
        {"kind": "rag", "field": "score", "scale": list(validation.RAG_SCALE)}
        if sorted(scale) == sorted(validation.RAG_SCALE)
        else {"kind": "scale", "field": "score", "scale": scale}
    )
    sections: list[dict[str, Any]] = []
    for raw_domain in _sequence(raw.get("domains"), "domains"):
        if not isinstance(raw_domain, Mapping):
            raise InvalidRubric("Each domain must be an object.")
        sections.append(
            {
                "kind": "domain",
                "id": raw_domain.get("id"),
                "title": raw_domain.get("label") or raw_domain.get("id"),
                "live": bool(raw_domain.get("live", False)),
                "instructions": _text(raw_domain.get("guidance")),
                "competencies": [
                    _v1_competency(raw_competency)
                    for raw_competency in _sequence(raw_domain.get("competencies"), "competencies")
                ],
                "competencyFields": [dict(spec) for spec in _V1_COMPETENCY_FIELDS],
            }
        )
    for raw_section in _sequence(raw.get("sections"), "sections"):
        if not isinstance(raw_section, Mapping):
            raise InvalidRubric("Each section must be an object.")
        sections.append({"kind": "field", "field": _v1_section_field(raw_section)})
    return {"schemaVersion": validation.SCHEMA_VERSION, "rating": rating, "sections": sections}


def _v1_competency(raw_competency: Any) -> dict[str, Any]:
    """A v1 competency: its guidance (if the uncommitted v1.5 wording had any) becomes instructions."""
    if not isinstance(raw_competency, Mapping):
        raise InvalidRubric("Each competency must be an object.")
    descriptors = raw_competency.get("descriptors") or {}
    if not isinstance(descriptors, Mapping):
        raise InvalidRubric(f"Competency {raw_competency.get('id')!r}'s descriptors must be an object.")
    return {
        "id": raw_competency.get("id"),
        "label": raw_competency.get("label") or raw_competency.get("id"),
        "instructions": _text(raw_competency.get("guidance")),
        "descriptors": {str(value): str(anchor) for value, anchor in descriptors.items()},
    }


def _v1_section_field(raw_section: Mapping[str, Any]) -> dict[str, Any]:
    """A v1 section as the one required top-level field it always was."""
    kind = str(raw_section.get("kind") or "text")
    section_id = str(raw_section.get("id") or "")
    if kind not in _V1_SECTION_KINDS:
        raise InvalidRubric(
            f"Section {section_id!r} is a {kind!r}; expected one of {list(_V1_SECTION_KINDS)}."
        )
    label = str(raw_section.get("label") or section_id)
    if kind == "list":
        return {"id": section_id, "label": label, "type": "list", "role": "summary"}
    if kind == "text":
        return {"id": section_id, "label": label, "type": "longText", "role": "summary"}
    schema = raw_section.get("schema")
    if not isinstance(schema, Mapping):
        raise InvalidRubric(f"Section {section_id!r} is an object and needs a schema describing it.")
    upgraded = field_from_schema(section_id, schema, required=True)
    upgraded["label"] = label
    return upgraded


# --- Parsing a valid version 2 structure into its dataclasses --------------------


def _rating(raw: Mapping[str, Any]) -> RatingSpec:
    """The rubric's rating. Already validated, so only read."""
    kind = str(raw["kind"])
    scale: tuple[str, ...] = ()
    if kind == "rag":
        scale = tuple(str(value) for value in raw.get("scale") or validation.RAG_SCALE)
    elif kind == "scale":
        scale = tuple(str(value) for value in raw["scale"])
    return RatingSpec(
        kind=kind,
        field=str(raw.get("field", "score")),
        scale=scale,
        minimum=raw.get("minimum") if kind == "range" else None,
        maximum=raw.get("maximum") if kind == "range" else None,
        step=str(raw.get("step", "number")),
    )


def _section(raw: Mapping[str, Any]) -> SectionSpec:
    """One domain, written section or lone field."""
    kind = str(raw["kind"])
    if kind == "field":
        lone = _field(raw["field"])
        return SectionSpec(id=lone.id, title=lone.label or lone.id, kind="field", fields=(lone,))
    return SectionSpec(
        id=str(raw["id"]),
        title=str(raw.get("title") or raw["id"]),
        kind=kind,
        instructions=_text(raw.get("instructions")),
        live=bool(raw.get("live", False)),
        nullable=bool(raw.get("nullable", False)),
        description=_text(raw.get("description")),
        required=bool(raw.get("required", True)),
        competencies=tuple(
            CompetencySpec(
                id=str(competency["id"]),
                label=str(competency.get("label") or competency["id"]),
                instructions=_text(competency.get("instructions")),
                descriptors={
                    str(value): str(anchor) for value, anchor in (competency.get("descriptors") or {}).items()
                },
            )
            for competency in raw.get("competencies") or ()
        ),
        competency_fields=tuple(_field(spec) for spec in raw.get("competencyFields") or ()),
        fields=tuple(_field(spec) for spec in raw.get("fields") or ()),
    )


def _field(raw: Mapping[str, Any]) -> FieldSpec:
    """One field, nested fields included."""
    return FieldSpec(
        id=str(raw["id"]),
        type=str(raw["type"]),
        label=str(raw.get("label") or ""),
        required=bool(raw.get("required", True)),
        instructions=_text(raw.get("instructions")),
        role=str(raw.get("role") or "other"),
        source=str(raw.get("source") or "marker"),
        nullable=bool(raw.get("nullable", False)),
        default=raw.get("default", NO_DEFAULT),
        example=raw.get("example"),
        min_items=raw.get("minItems"),
        options=tuple(str(option) for option in raw.get("options") or ()),
        fields=tuple(_field(child) for child in raw.get("fields") or ()),
    )


def _display(raw: Mapping[str, Any] | None) -> DisplaySpec:
    """How feedback and the dashboard read the rubric, as the author set it. Already validated."""
    if not raw:
        return DisplaySpec()
    domain = raw.get("domain") or {}
    total = raw.get("total") or {}
    return DisplaySpec(
        domain=DisplayDomain(aggregate=domain.get("aggregate"), pass_at_least=domain.get("passAtLeast")),
        total=DisplayTotal(
            aggregate=total.get("aggregate"),
            maximum=total.get("max"),
            pass_at_least=total.get("passAtLeast"),
            require_every_domain=bool(total.get("requireEveryDomain", False)),
        ),
        tones=tuple(
            DisplayTone(at_least=tone["atLeast"], tone=tone["tone"]) for tone in raw.get("tones") or ()
        ),
        bands=tuple(
            DisplayBand(
                start=band["from"], end=band["to"], label=str(band.get("label", "")), tone=band["tone"]
            )
            for band in raw.get("bands") or ()
        ),
        labels={str(key): str(value) for key, value in (raw.get("labels") or {}).items()},
    )


def _text(raw: Any) -> str:
    """Optional prose, kept verbatim: the marker reads it exactly as written."""
    return raw if isinstance(raw, str) else ""


def _sequence(raw: Any, what: str) -> list[Any]:
    """An optional list, refusing anything else in its place."""
    if raw is None:
        return []
    if not isinstance(raw, list | tuple):
        raise InvalidRubric(f"{what} must be a list.")
    return list(raw)


# --- Pacing -----------------------------------------------------------------------


def validate_pacing(raw: Mapping[str, Any] | None) -> dict[str, int]:
    """The consultation clock stored with a rubric, checked before it is saved.

    The same four marks the engine renders phase budgets from. They are checked
    here as well as there because a clock that cannot be run is a rubric that
    cannot be used, and the author should hear about it at the moment they
    write it rather than when a candidate starts a station.
    """
    raw_pacing = raw or {}
    try:
        pacing = {
            key: int(raw_pacing[key])
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


# --- Narrowing for feedback templates and reviews --------------------------------


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

    A template selects the domains its reviewers work through; the written
    sections are always kept, because they are what the candidate reads. An
    empty selection means the whole rubric, which is what an org that has not
    narrowed anything wants. A kept domain stays exactly as authored,
    nullable included.
    """
    wanted = reviewable_domains(field_selection)
    if not wanted:
        return structure
    unknown = sorted(wanted - {domain.id for domain in structure.domains})
    if unknown:
        raise InvalidRubric(f"The selection names {unknown}, which this rubric does not define.")
    return replace(
        structure,
        sections=tuple(
            section for section in structure.sections if section.kind != "domain" or section.id in wanted
        ),
    )


def frozen_structure(
    raw: Mapping[str, Any] | None, field_selection: Mapping[str, Any] | None
) -> dict[str, Any]:
    """The structure to freeze onto an attempt: version 2, narrowed like its framework.

    Stored as JSON beside the framework so the attempt is scored, and its
    feedback drawn, by the rules it was marked under, even after the rubric
    changes. Refuses what `parse_structure` refuses.
    """
    kept_domain_ids = {
        domain.id for domain in narrow_structure(parse_structure(raw), field_selection).domains
    }
    upgraded = upgrade_structure(raw or {})
    upgraded["sections"] = [
        section
        for section in upgraded.get("sections") or []
        if not isinstance(section, Mapping)
        or section.get("kind") != "domain"
        or section.get("id") in kept_domain_ids
    ]
    return upgraded


def scoring_domain_ids(structure: RubricStructure) -> frozenset[str]:
    """Domains a human review must score when using the full rubric."""
    return frozenset(domain.id for domain in structure.domains if domain.id not in NON_SCORING_SECTIONS)


# --- Display: feedback and dashboard ------------------------------------------------


def resolved_display(structure: RubricStructure) -> dict[str, Any]:
    """How feedback and the dashboard read this rubric, with every gap filled.

    The only place display defaults exist (plan §4.2). Whatever the author set
    wins; the rest comes from the rating kind:

    - `rag` / `scale`: domains as rating counts, the total as the share of the
      best value, no maximum; each value's tone from its place on the scale.
    - `range`: domains and total as sums. The total's maximum is the rating's
      maximum times the competencies a result answers: every non-nullable
      domain, plus the largest nullable one, since nullable domains are
      alternatives only one of which is filled (Ortho: 10 x 5 = 50).
    - `boolean`: domains and total as the percentage achieved, out of 100.

    Tones are fractions of the rating's maximum: 0.8 and up good, 0.6 fair,
    else poor, unless the author set their own. There is no pass line unless
    `passAtLeast` is set.
    """
    display, rating = structure.display, structure.rating
    domain_aggregate = display.domain.aggregate or _default_domain_aggregate(rating)
    total_aggregate = display.total.aggregate or _default_total_aggregate(rating)
    total_maximum = display.total.maximum
    if total_maximum is None:
        total_maximum = _total_maximum(structure, total_aggregate)
    return {
        "domain": {
            "aggregate": domain_aggregate,
            "max": _domain_maximum(structure, domain_aggregate),
            "passAtLeast": display.domain.pass_at_least,
        },
        "total": {
            "aggregate": total_aggregate,
            "max": total_maximum,
            "passAtLeast": display.total.pass_at_least,
            "requireEveryDomain": display.total.require_every_domain,
        },
        "tones": [{"atLeast": tone.at_least, "tone": tone.tone} for tone in display.tones]
        or _default_tones(rating),
        "bands": [
            {"from": band.start, "to": band.end, "label": band.label, "tone": band.tone}
            for band in display.bands
        ],
        "labels": dict(display.labels),
    }


def _default_domain_aggregate(rating: RatingSpec) -> str:
    """How a domain reads when the author did not say, by rating kind."""
    return {"range": "sum", "boolean": "percentAchieved"}.get(rating.kind, "ragCounts")


def _default_total_aggregate(rating: RatingSpec) -> str:
    """How the station total reads when the author did not say, by rating kind."""
    return {"range": "sum", "boolean": "percentAchieved"}.get(rating.kind, "ragShare")


def _rating_top(rating: RatingSpec) -> float:
    """The most one competency can earn: a range's maximum, or 1 for a met boolean."""
    return rating.maximum if rating.kind == "range" and rating.maximum is not None else 1


def _domain_maximum(structure: RubricStructure, aggregate: str) -> float | None:
    """The most a domain can read in its aggregate's units; None where there is no scale to fill."""
    if aggregate == "percentAchieved":
        return 100
    if aggregate == "mean":
        return _rating_top(structure.rating)
    if aggregate == "sum":
        largest = max((len(domain.competencies) for domain in structure.domains), default=0)
        return _rating_top(structure.rating) * largest
    return None


def _total_maximum(structure: RubricStructure, aggregate: str) -> float | None:
    """The most a station total can read in its aggregate's units."""
    if aggregate == "percentAchieved":
        return 100
    if aggregate == "mean":
        return _rating_top(structure.rating)
    if aggregate == "sum":
        always = sum(len(domain.competencies) for domain in structure.domains if not domain.nullable)
        alternatives = max(
            (len(domain.competencies) for domain in structure.domains if domain.nullable), default=0
        )
        return _rating_top(structure.rating) * (always + alternatives)
    return None


def _default_tones(rating: RatingSpec) -> list[dict[str, Any]]:
    """Colours for a rating nobody coloured, on the rating as a fraction of its maximum.

    An enumerated rating's value is placed by its position on the scale (best
    first): with G, A, R, G is 1, A is 0.5 and R is 0, so it takes the same
    tones as a number.
    """
    if rating.is_enumerated:
        count = len(rating.scale)
        return [
            {
                "value": value,
                "atLeast": 1 if count == 1 else round((count - 1 - index) / (count - 1), 4),
                "tone": _scale_tone(index, count),
            }
            for index, value in enumerate(rating.scale)
        ]
    return [
        {"atLeast": 0.8, "tone": "good"},
        {"atLeast": 0.6, "tone": "fair"},
        {"atLeast": 0, "tone": "poor"},
    ]


def _scale_tone(index: int, count: int) -> str:
    """Best value good, worst poor, anything between fair."""
    if index == 0:
        return "good"
    if index == count - 1:
        return "poor"
    return "fair"
