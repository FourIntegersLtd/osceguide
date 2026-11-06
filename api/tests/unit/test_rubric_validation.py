"""Every rule a version 2 rubric structure is checked against, one case each, with its literal message.

The messages are what an author reads in the rubric editor, so they are
asserted word for word: a rule that silently stopped firing, or started
saying something unhelpful, fails here.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any

import pytest

from app.features.rubrics import authoring, scheme
from app.features.rubrics.validation import IDENTIFIER_MESSAGE, validate_structure

VALID: dict[str, Any] = {
    "schemaVersion": 2,
    "rating": {"kind": "rag", "field": "score"},
    "sections": [
        {
            "kind": "domain",
            "id": "consulting",
            "title": "Consulting",
            "competencies": [{"id": "opens", "label": "Opens", "descriptors": {"G": "Does it."}}],
            "competencyFields": [
                {"id": "score", "type": "rating", "role": "rating"},
                {"id": "evidence", "type": "longText", "role": "evidence"},
            ],
        },
        {
            "kind": "section",
            "id": "feedback",
            "title": "Feedback",
            "fields": [{"id": "strengths", "type": "list", "role": "strength"}],
        },
    ],
}
RANGE_RATING = {"kind": "range", "field": "score", "minimum": 0, "maximum": 10, "step": "integer"}

Mutation = Callable[[dict[str, Any]], Any]


def _set(path: tuple[Any, ...], value: Any) -> Mutation:
    """A mutation setting one key, reached by a path of keys and indexes, to a value."""

    def mutate(structure: dict[str, Any]) -> None:
        """Walk to the parent and set the last key."""
        parent: Any = structure
        for step in path[:-1]:
            parent = parent[step]
        parent[path[-1]] = value

    return mutate


def _both(*mutations: Mutation) -> Mutation:
    """Several mutations applied in order."""

    def mutate(structure: dict[str, Any]) -> None:
        """Apply each one."""
        for mutation in mutations:
            mutation(structure)

    return mutate


def _feedback_fields(fields: list[dict[str, Any]]) -> Mutation:
    """Replace the written section's fields."""
    return _set(("sections", 1, "fields"), fields)


def _nested_groups(levels: int) -> dict[str, Any]:
    """A group nested `levels` deep, ending in one text field."""
    innermost: dict[str, Any] = {"id": "leaf", "type": "shortText"}
    for level in range(levels):
        innermost = {"id": f"group_{level}", "type": "group", "fields": [innermost]}
    return innermost


def test_the_valid_structure_has_no_problems() -> None:
    assert validate_structure(VALID) == []


RULES: list[tuple[str, Mutation, str, str]] = [
    ("schema version", _set(("schemaVersion",), 1), "schemaVersion", "This rubric must say schemaVersion 2."),
    (
        "rating missing",
        _set(("rating",), None),
        "rating",
        "A rubric needs a rating: how each competency is rated.",
    ),
    (
        "rating kind",
        _set(("rating", "kind"), "stars"),
        "rating.kind",
        "The rating kind must be one of rag, scale, range, boolean.",
    ),
    ("rating field id", _set(("rating", "field"), "Score"), "rating.field", IDENTIFIER_MESSAGE),
    (
        "rag scale",
        _set(("rating", "scale"), ["G", "A"]),
        "rating.scale",
        "An R/A/G rating's scale is G, A and R, each once.",
    ),
    (
        "empty scale",
        _both(
            _set(("rating",), {"kind": "scale", "scale": []}),
            _set(("sections", 0, "competencies", 0, "descriptors"), {}),
        ),
        "rating.scale",
        "A scale rating needs at least one value.",
    ),
    (
        "repeated scale value",
        _both(
            _set(("rating",), {"kind": "scale", "scale": ["pass", "pass"]}),
            _set(("sections", 0, "competencies", 0, "descriptors"), {}),
        ),
        "rating.scale",
        "The scale repeats a value; each must appear once.",
    ),
    (
        "range bounds",
        _both(
            _set(("rating",), {**RANGE_RATING, "minimum": 10}),
            _set(("sections", 0, "competencies", 0, "descriptors"), {}),
        ),
        "rating",
        "A range rating needs a minimum below its maximum.",
    ),
    (
        "range step",
        _both(
            _set(("rating",), {**RANGE_RATING, "step": "half"}),
            _set(("sections", 0, "competencies", 0, "descriptors"), {}),
        ),
        "rating.step",
        "A range's step must be number or integer.",
    ),
    (
        "no sections",
        _set(("sections",), []),
        "sections",
        "A rubric needs at least one section: it would ask the marker for nothing.",
    ),
    (
        "section not an object",
        _set(("sections", 1), "feedback"),
        "sections[1]",
        "Each section must be an object.",
    ),
    (
        "section kind",
        _set(("sections", 1, "kind"), "essay"),
        "sections[1].kind",
        "A section's kind must be one of domain, section, field.",
    ),
    (
        "section id",
        _set(("sections", 1, "id"), "Feedback!"),
        "sections[1].id",
        IDENTIFIER_MESSAGE,
    ),
    (
        "top-level id repeated",
        _set(("sections", 1, "id"), "consulting"),
        "sections[1].id",
        "'consulting' is already used by sections[0]; ids must differ.",
    ),
    (
        "written section with no fields",
        _feedback_fields([]),
        "sections[1].fields",
        "A written section needs at least one field.",
    ),
    (
        "domain with no competencies",
        _set(("sections", 0, "competencies"), []),
        "sections[0].competencies",
        "A domain needs at least one competency to rate.",
    ),
    (
        "domain with no rating field",
        _set(("sections", 0, "competencyFields"), [{"id": "evidence", "type": "longText"}]),
        "sections[0].competencyFields",
        "A domain rates each competency in exactly one rating field; this one has 0.",
    ),
    (
        "rating field named otherwise",
        _set(("sections", 0, "competencyFields", 0, "id"), "grade"),
        "sections[0].competencyFields[0].id",
        "The rating field must be called 'score', as the rubric's rating says.",
    ),
    (
        "competency id repeated",
        _set(
            ("sections", 0, "competencies"),
            [{"id": "opens", "label": "Opens"}, {"id": "opens", "label": "Again"}],
        ),
        "sections[0].competencies[1].id",
        "'opens' is already used by sections[0].competencies[0]; ids must differ.",
    ),
    (
        "competency not an object",
        _set(("sections", 0, "competencies"), ["opens"]),
        "sections[0].competencies[0]",
        "Each competency must be an object.",
    ),
    (
        "descriptors not an object",
        _set(("sections", 0, "competencies", 0, "descriptors"), ["G"]),
        "sections[0].competencies[0].descriptors",
        "Descriptors must be an object of rating value to text.",
    ),
    (
        "descriptor off the scale",
        _set(("sections", 0, "competencies", 0, "descriptors"), {"EXCELLENT": "..."}),
        "sections[0].competencies[0].descriptors.EXCELLENT",
        "'EXCELLENT' is not on the rating scale (G, A, R).",
    ),
    (
        "field not an object",
        _feedback_fields(["strengths"]),  # type: ignore[list-item]
        "sections[1].fields[0]",
        "Each field must be an object.",
    ),
    (
        "field id repeated",
        _feedback_fields([{"id": "strengths", "type": "list"}, {"id": "strengths", "type": "list"}]),
        "sections[1].fields[1].id",
        "'strengths' is already used by sections[1].fields[0]; ids must differ.",
    ),
    (
        "field type",
        _feedback_fields([{"id": "strengths", "type": "raw"}]),
        "sections[1].fields[0].type",
        "A field's type must be one of rating, shortText, longText, list, singleSelect, group, records.",
    ),
    (
        "field role",
        _feedback_fields([{"id": "strengths", "type": "list", "role": "praise"}]),
        "sections[1].fields[0].role",
        "A field's role must be one of rating, evidence, explanation, strength, improvement, action, flag, "
        "summary, selector, other.",
    ),
    (
        "field source",
        _feedback_fields([{"id": "strengths", "type": "list", "source": "examiner"}]),
        "sections[1].fields[0].source",
        "A field's source must be marker or system.",
    ),
    (
        "rating outside a domain's competency fields",
        _feedback_fields([{"id": "score", "type": "rating"}]),
        "sections[1].fields[0].type",
        "A rating field belongs only in a domain's competency fields.",
    ),
    (
        "lone field that is a rating",
        _set(("sections", 1), {"kind": "field", "field": {"id": "overall", "type": "rating"}}),
        "sections[1].field.type",
        "A rating field belongs only in a domain's competency fields.",
    ),
    (
        "minItems",
        _feedback_fields([{"id": "strengths", "type": "list", "minItems": -1}]),
        "sections[1].fields[0].minItems",
        "minItems must be a whole number, zero or more.",
    ),
    (
        "single select with no options",
        _feedback_fields([{"id": "station", "type": "singleSelect", "options": []}]),
        "sections[1].fields[0].options",
        "A single select needs at least one option.",
    ),
    (
        "group with no fields",
        _feedback_fields([{"id": "summary", "type": "group", "fields": []}]),
        "sections[1].fields[0].fields",
        "A group needs at least one field of its own.",
    ),
    (
        "display not an object",
        _set(("display",), "compact"),
        "display",
        "The display settings must be an object.",
    ),
    (
        "display parts not objects",
        _set(("display",), {"domain": "sum"}),
        "display",
        "display.domain and display.total must be objects.",
    ),
    (
        "domain aggregate",
        _set(("display",), {"domain": {"aggregate": "median"}}),
        "display.domain.aggregate",
        "A domain aggregate is one of ragCounts, sum, mean, percentAchieved.",
    ),
    (
        "total aggregate",
        _set(("display",), {"total": {"aggregate": "ragCounts"}}),
        "display.total.aggregate",
        "A total aggregate is one of ragShare, sum, mean, percentAchieved.",
    ),
    (
        "domain pass line",
        _set(("display",), {"domain": {"passAtLeast": -1}}),
        "display.domain.passAtLeast",
        "A domain pass line must be a number, zero or more.",
    ),
    (
        "total maximum",
        _set(("display",), {"total": {"max": "twelve"}}),
        "display.total.max",
        "A total's max and pass line must be numbers, zero or more.",
    ),
    (
        "pass line above the maximum",
        _set(("display",), {"total": {"max": 12, "passAtLeast": 13}}),
        "display.total.passAtLeast",
        "The pass line sits above the total's maximum.",
    ),
    (
        "every domain with no domain pass line",
        _set(("display",), {"total": {"requireEveryDomain": True}}),
        "display.total.requireEveryDomain",
        "Requiring every domain to pass needs a domain pass line (display.domain.passAtLeast).",
    ),
    (
        "mean pass line above the rating",
        _both(
            _set(("rating",), RANGE_RATING),
            _set(("sections", 0, "competencies", 0, "descriptors"), {}),
            _set(("display",), {"domain": {"aggregate": "mean", "passAtLeast": 11}}),
        ),
        "display.domain.passAtLeast",
        "The domain pass line sits above the rating's maximum (10).",
    ),
    (
        "tones on a scale rating",
        _set(("display",), {"tones": [{"atLeast": 0.8, "tone": "good"}]}),
        "display.tones",
        "A scale rating is coloured by each value's place on the scale; remove tones.",
    ),
    (
        "tones not a list",
        _both(
            _set(("rating",), RANGE_RATING),
            _set(("sections", 0, "competencies", 0, "descriptors"), {}),
            _set(("display",), {"tones": {}}),
        ),
        "display.tones",
        "Tones must be a list.",
    ),
    (
        "tone not an object",
        _both(
            _set(("rating",), RANGE_RATING),
            _set(("sections", 0, "competencies", 0, "descriptors"), {}),
            _set(("display",), {"tones": ["good"]}),
        ),
        "display.tones[0]",
        "Each tone must be an object.",
    ),
    (
        "tone threshold outside 0 to 1",
        _both(
            _set(("rating",), RANGE_RATING),
            _set(("sections", 0, "competencies", 0, "descriptors"), {}),
            _set(("display",), {"tones": [{"atLeast": 7, "tone": "good"}]}),
        ),
        "display.tones[0].atLeast",
        "atLeast is a fraction of the rating's maximum, from 0 to 1.",
    ),
    (
        "tone name",
        _both(
            _set(("rating",), RANGE_RATING),
            _set(("sections", 0, "competencies", 0, "descriptors"), {}),
            _set(("display",), {"tones": [{"atLeast": 0.5, "tone": "success"}]}),
        ),
        "display.tones[0].tone",
        "A tone is one of excellent, good, fair, weak, poor.",
    ),
    ("bands not a list", _set(("display",), {"bands": {}}), "display.bands", "Bands must be a list."),
    (
        "band not an object",
        _set(("display",), {"bands": [17]}),
        "display.bands[0]",
        "Each band must be an object.",
    ),
    (
        "band backwards",
        _set(("display",), {"bands": [{"from": 18, "to": 17, "tone": "poor"}]}),
        "display.bands[0]",
        "A band needs a from no greater than its to.",
    ),
    (
        "band above the maximum",
        _set(("display",), {"total": {"max": 50}, "bands": [{"from": 43, "to": 51, "tone": "good"}]}),
        "display.bands[0].to",
        "A band ends above the total's maximum.",
    ),
    (
        "band label",
        _set(("display",), {"bands": [{"from": 0, "to": 17, "label": 3, "tone": "poor"}]}),
        "display.bands[0].label",
        "A band's label must be text.",
    ),
    (
        "labels not an object",
        _set(("display",), {"labels": []}),
        "display.labels",
        "Labels must be an object of name to text.",
    ),
    (
        "unknown label",
        _set(("display",), {"labels": {"subtitle": "Overview"}}),
        "display.labels.subtitle",
        "Unknown label; the labels are title, domainSubtitle, domainPassLabel, totalTitle, "
        "trendSubtitle, passLabel.",
    ),
    (
        "label not text",
        _set(("display",), {"labels": {"title": 7}}),
        "display.labels.title",
        "A label must be text.",
    ),
    (
        "nesting depth",
        _feedback_fields([_nested_groups(8)]),
        "sections",
        "Fields nest 11 levels deep; the most a marker can fill is 10.",
    ),
    (
        "enum values",
        _feedback_fields(
            [{"id": "station", "type": "singleSelect", "options": [f"o{index}" for index in range(1001)]}]
        ),
        "sections",
        "The result has 1004 choice values; the most allowed is 1000.",
    ),
    (
        "name characters",
        _feedback_fields([{"id": "station", "type": "singleSelect", "options": ["x" * 120_001]}]),
        "sections",
        "Ids and choices add up to 120044 characters; the most allowed is 120000.",
    ),
    (
        "marked answers",
        _feedback_fields([{"id": f"note_{index}", "type": "shortText"} for index in range(401)]),
        "sections",
        "The marker would write 403 answers; the most allowed is 400. "
        "Remove 3 (fewer competencies, or fewer fields per competency).",
    ),
]


@pytest.mark.parametrize(
    ("mutation", "path", "message"), [rule[1:] for rule in RULES], ids=[rule[0] for rule in RULES]
)
def test_each_rule_says_what_is_wrong_and_where(mutation: Mutation, path: str, message: str) -> None:
    structure = copy.deepcopy(VALID)
    mutation(structure)

    assert validate_structure(structure) == [{"path": path, "message": message}]


def test_too_many_properties_is_refused() -> None:
    """Also more answers than allowed, so checked on its own rather than as the only problem."""
    structure = copy.deepcopy(VALID)
    _feedback_fields([{"id": f"note_{index}", "type": "shortText"} for index in range(5001)])(structure)

    assert {"path": "sections", "message": "The result has 5006 properties; the most allowed is 5000."} in (
        validate_structure(structure)
    )


def test_fields_that_are_not_a_list_are_refused() -> None:
    structure = copy.deepcopy(VALID)
    structure["sections"][1]["fields"] = {"id": "strengths"}

    assert {"path": "sections[1].fields", "message": "Fields must be a list."} in validate_structure(
        structure
    )


def test_a_structure_that_is_not_an_object_is_refused() -> None:
    assert validate_structure(["not", "a", "rubric"]) == [
        {"path": "", "message": "A rubric structure must be an object."}
    ]


# --- The author's scheme (schemaVersion 3): problems at their v3 paths -------------


def _second_domain_on_marks(structure: dict[str, Any]) -> None:
    structure["scales"].append({"id": "marks", "name": "0 to 10", "from": 0, "to": 10, "step": "whole"})
    structure["outline"].append(
        {
            "block": "domain",
            "id": "domain_2",
            "title": "Domain 2",
            "scale": "marks",
            "competencies": [{"id": "competency_2", "label": "Competency 2"}],
        }
    )


SCHEME_RULES: list[tuple[str, Mutation, str, str]] = [
    (
        "competency_id",
        _set(("outline", 0, "competencies", 0, "id"), "Bad Id"),
        "outline[0].competencies[0].id",
        IDENTIFIER_MESSAGE,
    ),
    (
        "unknown_scale",
        _set(("outline", 0, "scale"), "nope"),
        "outline[0].scale",
        "This domain uses a scale the scheme does not have.",
    ),
    (
        "rising_points",
        _set(("scales", 0, "levels", 1, "points"), 9),
        "scales[0].levels[1].points",
        "Points must not rise down the list: put the best level first.",
    ),
    (
        "rule_missing_level",
        _set(
            ("pass",),
            {
                "domain": {
                    "score": "labels",
                    "rule": {"type": "labels", "atLeast": 1, "of": "count", "value": "X"},
                }
            },
        ),
        "pass.domain.rule.value",
        "The rule names a level the scale does not have.",
    ),
    (
        "mixed_scales",
        _second_domain_on_marks,
        "outline[1].scale",
        "Domains use different scales. Use one scale for every domain for now.",
    ),
    (
        "no_outline",
        _set(("outline",), []),
        "outline",
        "Add a domain: the scheme would ask the marker for nothing.",
    ),
    (
        "every_domain_without_rule",
        _set(("pass",), {"overall": {"score": "labels", "everyDomainPasses": True}}),
        "pass.overall.everyDomainPasses",
        "Every domain must pass needs a domain pass rule.",
    ),
    (
        "bad_kind",
        _set(("competencyFeedback", 0, "kind"), "evidence"),
        "competencyFeedback[0].kind",
        "Pick what this feedback is: one of strengths, improvements, actions, quotes, "
        "summary, flags, reason, note.",
    ),
]


@pytest.mark.parametrize(
    ("mutation", "path", "message"),
    [rule[1:] for rule in SCHEME_RULES],
    ids=[rule[0] for rule in SCHEME_RULES],
)
def test_each_scheme_rule_says_what_is_wrong_and_where(mutation: Mutation, path: str, message: str) -> None:
    structure = copy.deepcopy(authoring.blank_scheme())
    mutation(structure)

    assert scheme.validate_scheme(structure) == [{"path": path, "message": message}]


def test_the_blank_scheme_has_no_problems() -> None:
    assert scheme.validate_scheme(authoring.blank_scheme()) == []


def test_a_compiled_problem_is_reported_at_its_block() -> None:
    assert scheme.scheme_path("sections[2].competencyFields[1].id") == "outline[2]"
    assert scheme.scheme_path("sections[0].competencies[3].label") == "outline[0].competencies[3]"
    assert scheme.scheme_path("rating.scale") == "scales"
    assert scheme.scheme_path("display.total.passAtLeast") == "pass.overall"
    assert scheme.scheme_path("display.domain.max") == "pass.domain"
    assert scheme.scheme_path("schemaVersion") == ""


def test_points_and_rule_in_the_compiled_form() -> None:
    wrong_length = copy.deepcopy(VALID)
    wrong_length["rating"] = {"kind": "rag", "field": "score", "points": [3, 2]}
    assert validate_structure(wrong_length) == [
        {"path": "rating.points", "message": "Points must give one number for each scale value."}
    ]
    ruled = copy.deepcopy(VALID)
    ruled["display"] = {
        "domain": {"rule": {"type": "labels", "atLeast": 1, "of": "count", "value": "A"}},
        "total": {"requireEveryDomain": True},
    }
    assert validate_structure(ruled) == []


def test_a_labels_rule_must_name_a_level_of_the_scale() -> None:
    ruled = copy.deepcopy(VALID)
    ruled["display"] = {
        "domain": {"rule": {"type": "labels", "atLeast": 1, "of": "count", "value": "X"}},
        "total": {},
    }
    assert [problem["path"] for problem in validate_structure(ruled)] != []


def test_requiring_every_domain_needs_a_domain_line_or_rule() -> None:
    ruled = copy.deepcopy(VALID)
    ruled["display"] = {"domain": {}, "total": {"requireEveryDomain": True}}
    assert validate_structure(ruled) != []
