"""What the candidate sees: shown and hidden fields, and the feedback tone an author picks.

The tone reaches the marker through the instructions frozen onto the attempt; the shown
fields reach the feedback screen through the frozen `display`.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from app.features.rubrics import domain
from app.features.rubrics.models import RubricVersion
from app.features.rubrics.service_marking import _snapshot_of
from tests.support.rubrics import PACING

ALL_SHOWN = {"overall": True, "areaScores": True, "wentWell": True, "workOn": True, "quotes": True}


def _structure(display: dict[str, Any] | None = None) -> dict[str, Any]:
    structure: dict[str, Any] = {
        "schemaVersion": 2,
        "rating": {"kind": "rag", "field": "score"},
        "sections": [
            {
                "kind": "domain",
                "id": "consulting",
                "title": "Consulting",
                "competencies": [{"id": "opens", "label": "Opens"}],
                "competencyFields": [{"id": "score", "type": "rating", "role": "rating"}],
            }
        ],
    }
    if display is not None:
        structure["display"] = display
    return structure


def _version(display: dict[str, Any] | None) -> RubricVersion:
    return RubricVersion(
        id=uuid.uuid4(),
        rubric_id=uuid.uuid4(),
        version=1,
        structure=_structure(display),
        system_prompt="Mark it.",
        pacing=PACING,
    )


def test_a_rubric_that_says_nothing_shows_every_field_and_sets_no_tone() -> None:
    display = domain.resolved_display(domain.parse_structure(_structure()))

    assert display["show"] == ALL_SHOWN
    assert display["feedbackTone"] is None


def test_a_hidden_field_and_a_tone_come_through_resolved_display() -> None:
    display = domain.resolved_display(
        domain.parse_structure(_structure({"show": {"quotes": False}, "feedbackTone": "brief"}))
    )

    assert display["show"] == {**ALL_SHOWN, "quotes": False}
    assert display["feedbackTone"] == "brief"


@pytest.mark.parametrize(
    ("display", "path", "message"),
    [
        (
            {"feedbackTone": "chatty"},
            "display.feedbackTone",
            "Choose a tone for the feedback: supportive, formal or brief.",
        ),
        ({"show": {"quotes": "no"}}, "display.show.quotes", "Choose Shown or Hidden."),
        (
            {"show": {"jokes": True}},
            "display.show.jokes",
            "This part of the feedback cannot be shown or hidden.",
        ),
    ],
)
def test_a_show_or_tone_the_screens_do_not_know_is_refused(
    display: dict[str, Any], path: str, message: str
) -> None:
    with pytest.raises(domain.InvalidRubric) as refused:
        domain.parse_structure(_structure(display))

    assert domain.validation_errors(refused.value) == [{"path": path, "message": message}]


def test_a_tone_is_added_to_the_marking_instructions_and_no_tone_leaves_them_alone() -> None:
    assert domain.prompt_with_tone("Mark it.", None) == "Mark it."
    assert domain.prompt_with_tone("Mark it.", "brief") == (
        "Mark it.\n\nKeep every piece of feedback brief: one short sentence per point."
    )
    assert domain.prompt_with_tone("Mark it.", "formal").endswith(
        "Write every piece of feedback in the formal tone of an examiner's report."
    )
    assert domain.prompt_with_tone("Mark it.", "supportive").endswith(
        "Write every piece of feedback in a supportive, direct tone: "
        "warm, specific and honest about what to change."
    )


def test_a_brief_tone_is_in_the_instructions_the_attempt_is_marked_with() -> None:
    snapshot = _snapshot_of(_version({"feedbackTone": "brief"}), "Scheme", None)

    assert snapshot["system_prompt"] == (
        "Mark it.\n\nKeep every piece of feedback brief: one short sentence per point."
    )
    assert snapshot["display"]["feedbackTone"] == "brief"


def test_an_existing_rubric_is_marked_with_its_instructions_unchanged() -> None:
    snapshot = _snapshot_of(_version(None), "Scheme", None)

    assert snapshot["system_prompt"] == "Mark it."
    assert snapshot["framework"]["system_prompt"] == "Mark it."
    assert snapshot["display"]["show"] == ALL_SHOWN
