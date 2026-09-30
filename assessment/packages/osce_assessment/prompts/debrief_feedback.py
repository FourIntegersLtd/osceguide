"""Renders a marked result for the debrief tutor, from the framework alone.

One walk serves every rubric. Domains and competencies come from the
framework, in its order and with its labels. Each field inside them is placed
and labelled by its role (evidence, missed items, critical flags and so on),
and every rating is worded from the framework's rating ("7/10", "Amber",
"competent"). No exam's field names or score units appear here: a new exam, or
an institution's own rubric, is rendered with no code change.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..contracts import CompetencyDomain, CompetencyFramework, FieldRole
from ..contracts.rating import number_text
from ._rating_text import rating_text

NO_MARKING = (
    "No marking is available for this consultation yet: it may still be being marked. "
    "Debrief from the transcript and from what the doctor tells you."
)

# The order fields are shown in inside a competency or group: the rating and
# its reasons first, then what went well and what did not, then what to do.
ROLE_ORDER: tuple[FieldRole, ...] = (
    "selector",
    "rating",
    "explanation",
    "evidence",
    "strength",
    "improvement",
    "flag",
    "action",
    "summary",
    "other",
)

# A few words after a field's label that tell the tutor what the field means,
# whatever the rubric author called it. Ratings, selectors and ``other`` fields
# speak for themselves.
ROLE_HINTS: dict[str, str] = {
    "explanation": "reason for the rating",
    "evidence": "evidence",
    "strength": "went well",
    "improvement": "to improve",
    "flag": "critical concern",
    "action": "next step",
    "summary": "summary",
}

# Markdown only has six heading levels.
DEEPEST_HEADING = 6


def render_marking(framework: CompetencyFramework, result: Mapping[str, Any] | None) -> str:
    """The whole marked result as markdown for the tutor, or ``NO_MARKING``.

    Order: any selector field (which part of the rubric applied), then each
    domain the result answered, then the written sections outside the domains
    (a narrative, actionable feedback). A nullable domain left null is skipped.
    """
    if not isinstance(result, Mapping) or not result:
        return NO_MARKING
    domain_ids = set(framework.domain_ids)
    loose_keys = _by_role(framework, [key for key in result if key not in domain_ids])
    selector_keys = [key for key in loose_keys if framework.role_of(key) == "selector"]
    section_keys = [key for key in loose_keys if key not in selector_keys]

    blocks = [_render_value(framework, key, result[key], heading_level=2) for key in selector_keys]
    for domain in framework.domains:
        domain_answer = result.get(domain.id)
        if isinstance(domain_answer, Mapping):
            blocks.append(_render_domain(framework, domain, domain_answer))
    blocks.extend(_render_value(framework, key, result[key], heading_level=2) for key in section_keys)

    text = "\n\n".join(block for block in blocks if block)
    return text or NO_MARKING


def _render_domain(framework: CompetencyFramework, domain: CompetencyDomain, answer: Mapping[str, Any]) -> str:
    """One domain: its rating summary, each competency, then its domain-level fields."""
    header_lines = [f"## {domain.label}"]
    summary = _domain_summary(framework, list(framework.scores_in({domain.id: answer}).values()))
    if summary:
        header_lines.append(summary)
    parts = ["\n".join(header_lines)]

    # Competencies in the framework's order, under the framework's labels.
    competencies = framework.competencies_in(domain.id)
    competency_keys = {competency.local_id for competency in competencies}
    for competency in competencies:
        competency_answer = answer.get(competency.local_id)
        if isinstance(competency_answer, Mapping):
            parts.append(_render_group(framework, competency.label, competency_answer, heading_level=3))

    # Anything else in the domain: fields answered once for the whole domain,
    # or competencies a schema-only framework does not list.
    other_keys = _by_role(framework, [key for key in answer if key not in competency_keys])
    parts.extend(_render_value(framework, key, answer[key], heading_level=3) for key in other_keys)
    return "\n\n".join(part for part in parts if part)


def _domain_summary(framework: CompetencyFramework, ratings: list[Any]) -> str:
    """One line summing up a domain's ratings in the rating's own units."""
    rating = framework.rating
    valid_ratings = [value for value in ratings if rating.accepts(value, framework.scale)]
    if not valid_ratings:
        return ""
    if rating.is_enumerated:
        counts = [
            f"{valid_ratings.count(scale_value)} {rating_text(rating, scale_value)}"
            for scale_value in framework.scale
            if scale_value in valid_ratings
        ]
        return "Ratings: " + ", ".join(counts)
    if rating.kind == "boolean":
        competent_count = sum(1 for value in valid_ratings if value is True)
        return f"Competent in {competent_count} of {len(valid_ratings)}"
    # A range: the total out of the most the rated competencies could score.
    assert rating.maximum is not None
    total = sum(valid_ratings)
    most_possible = rating.maximum * len(valid_ratings)
    return f"Total: {number_text(total)}/{number_text(most_possible)}"


def _render_group(
    framework: CompetencyFramework, title: str, answer: Mapping[str, Any], *, heading_level: int
) -> str:
    """A heading, then every field inside it in role order."""
    level = min(heading_level, DEEPEST_HEADING)
    lines = [f"{'#' * level} {title}"]
    for key in _by_role(framework, list(answer)):
        rendered = _render_value(framework, key, answer[key], heading_level=level + 1)
        if rendered:
            lines.append(rendered)
    return "\n".join(lines)


def _render_value(framework: CompetencyFramework, key: str, value: Any, *, heading_level: int) -> str:
    """One field of any shape: a group, a list of records, a list, or a single value."""
    if _is_empty(value):
        return ""
    role = framework.role_of(key)
    label = _label(key, role)
    if isinstance(value, Mapping):
        return _render_group(framework, _humanise(key), value, heading_level=heading_level)
    if role == "rating":
        return f"{label}: {rating_text(framework.rating, value)}"
    if isinstance(value, Sequence) and not isinstance(value, str):
        items = [item for item in value if not _is_empty(item)]
        if items and all(isinstance(item, Mapping) for item in items):
            # A list of records, e.g. prioritised actions each with its own steps.
            return "\n".join(
                _render_group(framework, f"{_humanise(key)} {position}", record, heading_level=heading_level)
                for position, record in enumerate(items, start=1)
            )
        return "\n".join([f"{label}:", *(f"- {_scalar_text(framework, item)}" for item in items)])
    return f"{label}: {_scalar_text(framework, value)}"


def _scalar_text(framework: CompetencyFramework, value: Any) -> str:
    """A single value as text; a bare yes/no reads as the rating would say it."""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return number_text(value)
    return str(value)


def _by_role(framework: CompetencyFramework, keys: list[str]) -> list[str]:
    """Keys in ``ROLE_ORDER``, keeping the result's own order within a role."""
    return sorted(keys, key=lambda key: ROLE_ORDER.index(framework.role_of(key)))


def _label(key: str, role: FieldRole) -> str:
    """A field's label, with a hint of its role so the tutor knows what it is."""
    hint = ROLE_HINTS.get(role)
    return f"{_humanise(key)} ({hint})" if hint else _humanise(key)


def _humanise(key: str) -> str:
    """``score_explanation`` -> ``Score explanation``."""
    words = key.replace("_", " ").strip()
    return words[:1].upper() + words[1:]


def _is_empty(value: Any) -> bool:
    """Whether a value says nothing worth showing (None, blank, or an empty list or map)."""
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (Mapping, list, tuple)):
        return len(value) == 0
    return False
