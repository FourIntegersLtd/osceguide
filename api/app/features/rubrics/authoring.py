"""What the rubric builder is handed besides the rubric itself (plan §8, Stage 4).

A sample result to preview the feedback with, the blank rubric an author starts
from, the wording a copied rubric keeps its origin by, and the draft
instructions "Generate draft instructions" offers.

Pure: no session, no models, no I/O. `service_authoring.py` does the reading.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any

from app.features.rubrics.structure import FieldSpec, RatingSpec, RubricStructure

# Where a copied rubric came from, kept on its structure so draft instructions
# can be read from the source later. `validation` ignores unknown top-level keys
# and the schema builder never reads it, so a model never sees it.
BASED_ON_KEY = "basedOn"

# The consultation clock a blank rubric starts with: twelve minutes, history
# taking by six, the introduction by thirty seconds, safety-netting in the last two.
BLANK_PACING: dict[str, int] = {
    "total_seconds": 720,
    "history_seconds": 360,
    "introduction_seconds": 30,
    "safety_net_seconds": 120,
}

BLANK_SYSTEM_PROMPT = (
    "You are an experienced OSCE examiner. Read the whole consultation transcript, "
    "then fill every field of the schema. Rate each competency on the rubric's own "
    "scale, quote or paraphrase the transcript as evidence, and explain each rating "
    "by what the candidate did or missed."
)

# Fractions of a range rating a sample walks through, competency by competency,
# so the preview shows a spread rather than one value everywhere.
_RANGE_FRACTIONS = (0.9, 0.7, 0.5, 0.3)
_BOOLEAN_SAMPLES = (True, True, False)
_SAMPLE_ITEMS = 2


def blank_structure() -> dict[str, Any]:
    """The smallest publishable rubric in the v2 shape (the fixture; `blank_scheme` is the v3 draft).

    R/A/G, one domain, one competency.

    Every competency answers a rating, the evidence for it and why, which is
    what every platform exam asks too.
    """
    return {
        "schemaVersion": 2,
        "rating": {"kind": "rag", "field": "score"},
        "sections": [
            {
                "id": "domain_1",
                "title": "Domain 1",
                "kind": "domain",
                "instructions": "",
                "competencies": [{"id": "competency_1", "label": "Competency 1", "instructions": ""}],
                "competencyFields": [
                    {"id": "score", "type": "rating", "role": "rating", "label": "Rating"},
                    {"id": "evidence", "type": "longText", "role": "evidence", "label": "Evidence"},
                    {"id": "explanation", "type": "longText", "role": "explanation", "label": "Explanation"},
                ],
            }
        ],
    }


def blank_scheme() -> dict[str, Any]:
    """The smallest publishable scheme, as an author starts it: R/A/G, one domain, one competency."""
    return {
        "schemaVersion": 3,
        "mark": {"field": "score", "role": "rating", "label": "Rating"},
        "scales": [
            {
                "id": "rag",
                "name": "RAG",
                "levels": [
                    {"value": "G", "label": "Green", "points": 3},
                    {"value": "A", "label": "Amber", "points": 2},
                    {"value": "R", "label": "Red", "points": 1},
                ],
            }
        ],
        "outline": [
            {
                "block": "domain",
                "id": "domain_1",
                "title": "Domain 1",
                "instructions": "",
                "scale": "rag",
                "competencies": [{"id": "competency_1", "label": "Competency 1", "instructions": ""}],
            }
        ],
        "competencyFeedback": [
            {"id": "evidence", "kind": "quotes", "shape": "paragraph", "label": "Evidence"},
            {"id": "explanation", "kind": "reason", "shape": "paragraph", "label": "Explanation"},
        ],
    }


def with_origin(structure: Mapping[str, Any], *, rubric_id: str, version: int, title: str) -> dict[str, Any]:
    """A copy of `structure` that remembers the published version it was copied from."""
    copied = dict(structure)
    copied[BASED_ON_KEY] = {"rubricId": rubric_id, "version": version, "title": title}
    return copied


def origin_of(structure: Mapping[str, Any]) -> tuple[str, int] | None:
    """The (rubric id, version) a structure was copied from, when it says so."""
    based_on = structure.get(BASED_ON_KEY)
    if not isinstance(based_on, Mapping):
        return None
    rubric_id, version = based_on.get("rubricId"), based_on.get("version")
    if isinstance(rubric_id, str) and isinstance(version, int) and not isinstance(version, bool):
        return rubric_id, version
    return None


# --- A sample result ---------------------------------------------------------------


class _RatingCycle:
    """Hands out one rating per competency, walking the scale so the sample is varied."""

    def __init__(self, rating: RatingSpec) -> None:
        """Start at the first competency."""
        self.rating = rating
        self.index = 0

    def next_value(self) -> Any:
        """The next competency's rating, in the rubric's own units."""
        position = self.index
        self.index += 1
        rating = self.rating
        if rating.is_enumerated:
            return rating.scale[position % len(rating.scale)]
        if rating.kind == "boolean":
            return _BOOLEAN_SAMPLES[position % len(_BOOLEAN_SAMPLES)]
        minimum = rating.minimum if rating.minimum is not None else 0
        maximum = rating.maximum if rating.maximum is not None else 1
        value = minimum + (maximum - minimum) * _RANGE_FRACTIONS[position % len(_RANGE_FRACTIONS)]
        return round(value) if rating.step == "integer" else round(value, 2)


def sample_result(structure: RubricStructure) -> dict[str, Any]:
    """A made-up result this rubric's marker schema accepts, for previewing its feedback.

    Deterministic, so a preview does not flicker between saves. Only what the
    marker writes: system fields are filled later by the platform, never by a
    model. Of the nullable domains and sections (a station's variants), only
    the first is filled, the way a marker fills the one variant it saw.
    """
    ratings = _RatingCycle(structure.rating)
    result: dict[str, Any] = {}
    first_nullable_filled = False
    for section in structure.sections:
        if section.kind == "field":
            for lone_field in _marker_fields(section.fields):
                result[lone_field.id] = _sample_field(lone_field, ratings, section.title)
            continue
        if section.nullable:
            if first_nullable_filled:
                result[section.id] = None
                continue
            first_nullable_filled = True
        answer: dict[str, Any] = {}
        for competency in section.competencies:
            answer[competency.id] = {
                spec.id: _sample_field(spec, ratings, competency.label)
                for spec in _marker_fields(section.competency_fields)
            }
        for section_field in _marker_fields(section.fields):
            answer[section_field.id] = _sample_field(section_field, ratings, section.title)
        result[section.id] = answer
    return result


def _marker_fields(fields: tuple[FieldSpec, ...]) -> list[FieldSpec]:
    """The fields a marker writes: every one not filled in by the platform."""
    return [spec for spec in fields if spec.source != "system"]


def _sample_field(spec: FieldSpec, ratings: _RatingCycle, owner_label: str) -> Any:
    """One field's sample answer, by its type."""
    name = spec.label or spec.id.replace("_", " ")
    if spec.type == "rating":
        return ratings.next_value()
    if spec.type == "shortText":
        return f"{name} for {owner_label}"
    if spec.type == "longText":
        return f"Sample {name.lower()} for {owner_label}."
    if spec.type == "singleSelect":
        return spec.options[0] if spec.options else ""
    if spec.type == "group":
        return {child.id: _sample_field(child, ratings, owner_label) for child in _marker_fields(spec.fields)}
    item_count = max(_SAMPLE_ITEMS, spec.min_items or 0)
    if spec.type == "records":
        return [
            {child.id: _sample_field(child, ratings, owner_label) for child in _marker_fields(spec.fields)}
            for _ in range(item_count)
        ]
    return [f"{name} {number}" for number in range(1, item_count + 1)]


# --- Instructions by path ----------------------------------------------------------


@dataclass(frozen=True)
class InstructionSlot:
    """One place in a structure that carries instructions, and what it is."""

    # Index-based, as a validation error's path is: `sections[0].competencies[1]`.
    path: str
    # Qualified by ids, as a result is keyed and `profile_of` names it.
    key: str
    # domain, competency, section or field.
    kind: str
    # A field's role; for the others, the same as `kind`.
    role: str
    # The wording it has now; empty when the author has not written any.
    current: str


def instruction_slots(structure: Mapping[str, Any]) -> Iterator[InstructionSlot]:
    """Every place a version 2 structure carries instructions, in authored order.

    Keys are qualified the way results are keyed: `domain`, `domain.competency`,
    `domain.*.field` for what every competency answers, `domain.field` for what
    the domain answers once, `section` and `section.field`, nested with dots,
    and a lone field by its own id. Anything malformed is skipped rather than
    refused: a draft is allowed to be half-written.
    """
    sections = structure.get("sections")
    if not isinstance(sections, list):
        return
    for section_index, section in enumerate(sections):
        if not isinstance(section, Mapping):
            continue
        section_path = f"sections[{section_index}]"
        section_id = str(section.get("id") or "")
        if section.get("kind") == "field":
            yield from _field_slots([section.get("field")], f"{section_path}.field", "", single=True)
            continue
        kind = "domain" if section.get("kind") == "domain" else "section"
        yield InstructionSlot(section_path, section_id, kind, kind, _text(section.get("instructions")))
        competencies = section.get("competencies")
        for competency_index, competency in enumerate(competencies if isinstance(competencies, list) else []):
            if isinstance(competency, Mapping):
                yield InstructionSlot(
                    f"{section_path}.competencies[{competency_index}]",
                    f"{section_id}.{competency.get('id') or ''}",
                    "competency",
                    "competency",
                    _text(competency.get("instructions")),
                )
        yield from _field_slots(
            section.get("competencyFields"), f"{section_path}.competencyFields", f"{section_id}.*"
        )
        yield from _field_slots(section.get("fields"), f"{section_path}.fields", section_id)


def _field_slots(
    raw_fields: Any, list_path: str, prefix: str, *, single: bool = False
) -> Iterator[InstructionSlot]:
    """Every field in a list (or the one lone field), and the fields nested in each."""
    if not isinstance(raw_fields, list):
        return
    for field_index, spec in enumerate(raw_fields):
        if not isinstance(spec, Mapping):
            continue
        field_path = list_path if single else f"{list_path}[{field_index}]"
        field_id = str(spec.get("id") or "")
        key = f"{prefix}.{field_id}" if prefix else field_id
        role = spec.get("role")
        yield InstructionSlot(
            field_path,
            key,
            "field",
            role if isinstance(role, str) else "other",
            _text(spec.get("instructions")),
        )
        yield from _field_slots(spec.get("fields"), f"{field_path}.fields", key)


def profile_of(structure: Mapping[str, Any]) -> dict[str, str]:
    """Every instruction a version 2 structure carries, keyed by its qualified path.

    What `scripts/generate_platform_seed.py` writes to `profiles/<exam>.json`,
    and what "Generate draft instructions" reads from a copied rubric's source.
    """
    return {slot.key: slot.current for slot in instruction_slots(structure) if slot.current}


def draft_instructions(
    structure: Mapping[str, Any], source_profile: Mapping[str, str], generic: Mapping[str, str]
) -> list[tuple[InstructionSlot, str, str]]:
    """Suggested wording for every slot: (slot, text, where it came from).

    The source rubric's own wording for the same key wins; otherwise the
    generic wording for the slot's role (a field) or kind. A slot with neither
    is left out, and so is one whose role has no generic wording (`other`).
    """
    drafts: list[tuple[InstructionSlot, str, str]] = []
    for slot in instruction_slots(structure):
        if source_profile.get(slot.key):
            drafts.append((slot, source_profile[slot.key], "rubric"))
        elif generic.get(slot.role):
            drafts.append((slot, generic[slot.role], "generic"))
    return drafts


def _text(raw: Any) -> str:
    """Instructions as text; anything else counts as none written."""
    return raw if isinstance(raw, str) else ""
