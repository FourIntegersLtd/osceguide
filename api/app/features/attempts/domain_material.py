"""Splitting a station document into what a candidate may see, and when.

Pure rules, no session: which keys of `station_versions.content` belong to the
brief, which to the review, and how to read a block that is a list in one
exam's documents and a string in another's. `service_material` does the IO and
these decide what comes out of it.

Beside `domain_definition`, which answers the same question for the worker.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

# The document keys each screen is allowed to see. Named rather than derived:
# a station gains keys as exams are added, and a rule that said "everything
# except the patient block" would hand over each new one by default.
PATIENT_BLOCKS = ("patient_information", "patient_info")

# Ortho's stations put candidate-facing material flat on the document rather
# than in a `doctor_information` block, because an interview or a trauma list
# is not a consultation. These two tuples are that difference, named once.
SCENARIO_KEYS = (
    "station_type",
    "clinical_scenario_title",
    "clinical_scenario",
    "radiograph_image_url",
    "additional_image_urls",
    "background_overview",
    "patient_list_for_candidate",
    "duration_minutes",
)

TEACHING_KEYS = (
    "key_concerns",
    "history_overview",
    "examination_overview",
    "investigations_overview",
    "management_overview",
    "interview_questions",
    "references",
    "examiner_additional_info",
    "suggested_order_overview",
    "suggested_order",
    "communication_themes",
    "consent_approach",
    "breaking_bad_news_framework",
    "professional_conduct_topics",
    "key_learning_points",
    "portfolio_themes",
)


def block(content: Mapping[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    """The first of these keys holding a mapping, or an empty one."""
    for key in keys:
        value = content.get(key)
        if isinstance(value, Mapping):
            return dict(value)
    return {}


def scenario(content: Mapping[str, Any]) -> dict[str, Any] | None:
    """Ortho's candidate-facing material that sits flat on the document, or `None` if there is none."""
    present = {key: content[key] for key in SCENARIO_KEYS if key in content}
    return present or None


def text(value: Any) -> str | None:
    """A block's value as trimmed text, or `None` if it holds nothing."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def lines(value: Any) -> list[str]:
    """A block that is a list in one exam and a single string in another."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, Mapping):
        return [str(item).strip() for item in value.values() if str(item).strip()]
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


def teaching(content: Mapping[str, Any]) -> dict[str, Any]:
    """Ortho's debrief material: the keys that sit flat beside the plan."""
    return {key: content[key] for key in TEACHING_KEYS if key in content}
