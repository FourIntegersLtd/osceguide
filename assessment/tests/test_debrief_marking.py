"""The debrief tutor's view of a marked result is walked by role, never by field name.

Each test builds a framework as data and asserts the literal text the tutor
reads, so a rubric nobody has seen before renders with no code change.
"""

from __future__ import annotations

from osce_assessment.contracts import CompetencyFramework, Rating
from osce_assessment.prompts import NO_MARKING, rating_text, render_marking


def fifth_exam(**overrides: object) -> CompetencyFramework:
    """A made-up rubric: two domains (one nullable), whole-number ratings 1..5."""
    payload: dict[str, object] = {
        "id": "fifth-exam-v1",
        "label": "Fifth exam",
        "scale": [],
        "rating": {"kind": "range", "minimum": 1, "maximum": 5, "step": "integer"},
        "rating_field": "mark",
        "domains": [
            {"id": "consulting", "label": "Consulting"},
            {"id": "viva", "label": "Viva", "nullable": True},
        ],
        "competencies": [
            {"id": "consulting.opening", "label": "Opening", "domain_id": "consulting"},
            {"id": "viva.opening", "label": "Viva opening", "domain_id": "viva"},
        ],
        "field_roles": {"why": "explanation", "worries": "flag", "next": "action", "story": "summary"},
    }
    payload.update(overrides)
    return CompetencyFramework.model_validate(payload)


def test_a_new_rubric_renders_by_role_with_no_code_for_it() -> None:
    result = {
        "consulting": {"opening": {"next": ["Set an agenda"], "why": "Rushed.", "mark": 3, "worries": ["No safety net"]}},
        "viva": None,
        "story": "Solid but abrupt.",
    }
    assert render_marking(fifth_exam(), result) == (
        "## Consulting\n"
        "Total: 3/5\n"
        "\n"
        "### Opening\n"
        "Mark: 3/5\n"
        "Why (reason for the rating): Rushed.\n"
        "Worries (critical concern):\n"
        "- No safety net\n"
        "Next (next step):\n"
        "- Set an agenda\n"
        "\n"
        "Story (summary): Solid but abrupt."
    )


def test_a_v1_framework_with_no_roles_still_shows_every_field() -> None:
    """Before platform-api sends field roles, nothing the marker wrote is lost."""
    framework = fifth_exam(field_roles={}, rating_field=None, rating={"kind": "rag"}, scale=["G", "A", "R"])
    rendered = render_marking(framework, {"consulting": {"opening": {"mark": "A", "why": "Rushed."}}})
    assert rendered == "## Consulting\n\n### Opening\nMark: A\nWhy: Rushed."


def test_no_result_says_so_rather_than_inventing_one() -> None:
    assert render_marking(fifth_exam(), None) == NO_MARKING
    assert render_marking(fifth_exam(), {}) == NO_MARKING
    assert render_marking(fifth_exam(), {"viva": None}) == NO_MARKING


def test_a_rating_is_worded_from_its_kind() -> None:
    assert rating_text(Rating(kind="range", minimum=0, maximum=10, step="integer"), 7) == "7/10"
    assert rating_text(Rating(kind="range", minimum=0, maximum=10, step="integer"), 7, spoken=True) == "7 out of 10"
    assert rating_text(Rating(kind="range", minimum=0, maximum=1), 0.75) == "0.75/1"
    assert rating_text(Rating(kind="rag"), "A") == "Amber"
    assert rating_text(Rating(kind="rag"), "A", spoken=True) == "competent"
    assert rating_text(Rating(kind="boolean"), True) == "competent"
    assert rating_text(Rating(kind="boolean"), False) == "not yet competent"
    assert rating_text(Rating(kind="scale"), "Adequate") == "Adequate"


def test_a_boolean_domain_is_summed_up_as_competent_of_total() -> None:
    framework = fifth_exam(rating={"kind": "boolean"}, rating_field="competent")
    rendered = render_marking(framework, {"consulting": {"opening": {"competent": False}}})
    assert rendered.splitlines()[:4] == ["## Consulting", "Competent in 0 of 1", "", "### Opening"]
    assert "Competent: not yet competent" in rendered
