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
    (
        "schema version",
        _set(("schemaVersion",), 1),
        "schemaVersion",
        "This marking scheme is in an old or unknown format. Open it in the marking scheme builder and "
        "save it again.",
    ),
    (
        "rating missing",
        _set(("rating",), None),
        "rating",
        "Add a rating scale so markers know how to rate each Competency, for example Good, Fair and Poor.",
    ),
    (
        "rating kind",
        _set(("rating", "kind"), "stars"),
        "rating.kind",
        "Choose how Competencies are rated: red, amber and green; named levels such as Good and Fair; a "
        "number range; or yes and no.",
    ),
    ("rating field id", _set(("rating", "field"), "Score"), "rating.field", IDENTIFIER_MESSAGE),
    (
        "rag scale",
        _set(("rating", "scale"), ["G", "A"]),
        "rating.scale",
        "A red, amber and green rating must use Green, Amber and Red (G, A and R), each once.",
    ),
    (
        "empty scale",
        _both(
            _set(("rating",), {"kind": "scale", "scale": []}),
            _set(("sections", 0, "competencies", 0, "descriptors"), {}),
        ),
        "rating.scale",
        "A rating scale needs at least one level, such as Good.",
    ),
    (
        "repeated scale value",
        _both(
            _set(("rating",), {"kind": "scale", "scale": ["pass", "pass"]}),
            _set(("sections", 0, "competencies", 0, "descriptors"), {}),
        ),
        "rating.scale",
        "A level appears twice on the rating scale. Each level can appear only once.",
    ),
    (
        "range bounds",
        _both(
            _set(("rating",), {**RANGE_RATING, "minimum": 10}),
            _set(("sections", 0, "competencies", 0, "descriptors"), {}),
        ),
        "rating",
        "A number range needs a lowest number that is smaller than the highest, for example 1 to 5.",
    ),
    (
        "range step",
        _both(
            _set(("rating",), {**RANGE_RATING, "step": "half"}),
            _set(("sections", 0, "competencies", 0, "descriptors"), {}),
        ),
        "rating.step",
        "Choose whether markers give any number, including decimals, or whole numbers only.",
    ),
    (
        "no sections",
        _set(("sections",), []),
        "sections",
        "Add at least one Domain or section, otherwise the marker has nothing to mark.",
    ),
    (
        "section not an object",
        _set(("sections", 1), "feedback"),
        "sections[1]",
        "This section is not set up correctly. Remove it and add it again.",
    ),
    (
        "section kind",
        _set(("sections", 1, "kind"), "essay"),
        "sections[1].kind",
        "Each part of the marking scheme must be a Domain, a written section or a single question.",
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
        "The name 'consulting' is already used in this list. Give each item its own name.",
    ),
    (
        "written section with no fields",
        _feedback_fields([]),
        "sections[1].fields",
        "A written section needs at least one question for the marker to answer.",
    ),
    (
        "domain with no competencies",
        _set(("sections", 0, "competencies"), []),
        "sections[0].competencies",
        "Add at least one Competency to this Domain.",
    ),
    (
        "domain with no rating field",
        _set(("sections", 0, "competencyFields"), [{"id": "evidence", "type": "longText"}]),
        "sections[0].competencyFields",
        "Each Domain needs exactly one rating for its Competencies; this one has 0.",
    ),
    (
        "rating field named otherwise",
        _set(("sections", 0, "competencyFields", 0, "id"), "grade"),
        "sections[0].competencyFields[0].id",
        "The rating in this Domain must use the same name as the marking scheme's rating, which is 'score'.",
    ),
    (
        "competency id repeated",
        _set(
            ("sections", 0, "competencies"),
            [{"id": "opens", "label": "Opens"}, {"id": "opens", "label": "Again"}],
        ),
        "sections[0].competencies[1].id",
        "The name 'opens' is already used in this list. Give each item its own name.",
    ),
    (
        "competency not an object",
        _set(("sections", 0, "competencies"), ["opens"]),
        "sections[0].competencies[0]",
        "This Competency is not set up correctly. Remove it and add it again.",
    ),
    (
        "descriptors not an object",
        _set(("sections", 0, "competencies", 0, "descriptors"), ["G"]),
        "sections[0].competencies[0].descriptors",
        "The descriptions for each level are not set up correctly. Write one short description per level.",
    ),
    (
        "descriptor off the scale",
        _set(("sections", 0, "competencies", 0, "descriptors"), {"EXCELLENT": "..."}),
        "sections[0].competencies[0].descriptors.EXCELLENT",
        "The description for 'EXCELLENT' does not match a level on the rating scale (G, A, R). Use one of "
        "those levels, or remove it.",
    ),
    (
        "field not an object",
        _feedback_fields(["strengths"]),  # type: ignore[list-item]
        "sections[1].fields[0]",
        "This question is not set up correctly. Remove it and add it again.",
    ),
    (
        "field id repeated",
        _feedback_fields([{"id": "strengths", "type": "list"}, {"id": "strengths", "type": "list"}]),
        "sections[1].fields[1].id",
        "The name 'strengths' is already used in this list. Give each item its own name.",
    ),
    (
        "field type",
        _feedback_fields([{"id": "strengths", "type": "raw"}]),
        "sections[1].fields[0].type",
        "Choose what kind of answer this question needs, such as short text, long text, a list or a choice.",
    ),
    (
        "field role",
        _feedback_fields([{"id": "strengths", "type": "list", "role": "praise"}]),
        "sections[1].fields[0].role",
        "Choose what this question is used for.",
    ),
    (
        "field source",
        _feedback_fields([{"id": "strengths", "type": "list", "source": "examiner"}]),
        "sections[1].fields[0].source",
        "Choose who fills this in: the marker or the system.",
    ),
    (
        "rating outside a domain's competency fields",
        _feedback_fields([{"id": "score", "type": "rating"}]),
        "sections[1].fields[0].type",
        "A rating can only be added to a Competency inside a Domain.",
    ),
    (
        "lone field that is a rating",
        _set(("sections", 1), {"kind": "field", "field": {"id": "overall", "type": "rating"}}),
        "sections[1].field.type",
        "A rating can only be added to a Competency inside a Domain.",
    ),
    (
        "minItems",
        _feedback_fields([{"id": "strengths", "type": "list", "minItems": -1}]),
        "sections[1].fields[0].minItems",
        "The minimum number of entries must be a whole number, 0 or more.",
    ),
    (
        "single select with no options",
        _feedback_fields([{"id": "station", "type": "singleSelect", "options": []}]),
        "sections[1].fields[0].options",
        "A question with a list of choices needs at least one choice.",
    ),
    (
        "group with no fields",
        _feedback_fields([{"id": "summary", "type": "group", "fields": []}]),
        "sections[1].fields[0].fields",
        "A grouped question needs at least one question inside it.",
    ),
    (
        "display not an object",
        _set(("display",), "compact"),
        "display",
        "The feedback display settings are not set up correctly.",
    ),
    (
        "display parts not objects",
        _set(("display",), {"domain": "sum"}),
        "display",
        "The Domain and total display settings are not set up correctly.",
    ),
    (
        "domain aggregate",
        _set(("display",), {"domain": {"aggregate": "median"}}),
        "display.domain.aggregate",
        "Choose how each Domain's score is worked out: add up, average, percentage or count of ratings.",
    ),
    (
        "total aggregate",
        _set(("display",), {"total": {"aggregate": "ragCounts"}}),
        "display.total.aggregate",
        "Choose how the total score is worked out: add up, average, percentage or share of ratings.",
    ),
    (
        "domain pass line",
        _set(("display",), {"domain": {"passAtLeast": -1}}),
        "display.domain.passAtLeast",
        "A Domain's pass mark must be a number, 0 or more.",
    ),
    (
        "total maximum",
        _set(("display",), {"total": {"max": "twelve"}}),
        "display.total.max",
        "The total marks and the overall pass mark must be numbers, 0 or more.",
    ),
    (
        "pass line above the maximum",
        _set(("display",), {"total": {"max": 12, "passAtLeast": 13}}),
        "display.total.passAtLeast",
        "The overall pass mark is higher than the most marks anyone can get. Lower it.",
    ),
    (
        "every domain with no domain pass line",
        _set(("display",), {"total": {"requireEveryDomain": True}}),
        "display.total.requireEveryDomain",
        "To require every Domain to pass, set a pass mark for each Domain first.",
    ),
    (
        "mean pass line above the rating",
        _both(
            _set(("rating",), RANGE_RATING),
            _set(("sections", 0, "competencies", 0, "descriptors"), {}),
            _set(("display",), {"domain": {"aggregate": "mean", "passAtLeast": 11}}),
        ),
        "display.domain.passAtLeast",
        "A Domain's pass mark is higher than the highest rating (10). Lower it.",
    ),
    (
        "tones on a scale rating",
        _set(("display",), {"tones": [{"atLeast": 0.8, "tone": "good"}]}),
        "display.tones",
        "Named levels are coloured automatically by their place on the scale, so remove the custom colours.",
    ),
    (
        "tones not a list",
        _both(
            _set(("rating",), RANGE_RATING),
            _set(("sections", 0, "competencies", 0, "descriptors"), {}),
            _set(("display",), {"tones": {}}),
        ),
        "display.tones",
        "The score colours are not set up correctly. Remove them and add them again.",
    ),
    (
        "tone not an object",
        _both(
            _set(("rating",), RANGE_RATING),
            _set(("sections", 0, "competencies", 0, "descriptors"), {}),
            _set(("display",), {"tones": ["good"]}),
        ),
        "display.tones[0]",
        "This score colour is not set up correctly. Remove it and add it again.",
    ),
    (
        "tone threshold outside 0 to 1",
        _both(
            _set(("rating",), RANGE_RATING),
            _set(("sections", 0, "competencies", 0, "descriptors"), {}),
            _set(("display",), {"tones": [{"atLeast": 7, "tone": "good"}]}),
        ),
        "display.tones[0].atLeast",
        "A colour starts at a share of the highest rating, from 0 (none of it) to 1 (all of it).",
    ),
    (
        "tone name",
        _both(
            _set(("rating",), RANGE_RATING),
            _set(("sections", 0, "competencies", 0, "descriptors"), {}),
            _set(("display",), {"tones": [{"atLeast": 0.5, "tone": "success"}]}),
        ),
        "display.tones[0].tone",
        "Choose a colour: excellent, good, fair, weak, poor.",
    ),
    (
        "bands not a list",
        _set(("display",), {"bands": {}}),
        "display.bands",
        "The score bands are not set up correctly. Remove them and add them again.",
    ),
    (
        "band not an object",
        _set(("display",), {"bands": [17]}),
        "display.bands[0]",
        "This score band is not set up correctly. Remove it and add it again.",
    ),
    (
        "band backwards",
        _set(("display",), {"bands": [{"from": 18, "to": 17, "tone": "poor"}]}),
        "display.bands[0]",
        "A score band must start at or below the number where it ends.",
    ),
    (
        "band above the maximum",
        _set(("display",), {"total": {"max": 50}, "bands": [{"from": 43, "to": 51, "tone": "good"}]}),
        "display.bands[0].to",
        "A score band ends above the highest possible total. Lower it.",
    ),
    (
        "band label",
        _set(("display",), {"bands": [{"from": 0, "to": 17, "label": 3, "tone": "poor"}]}),
        "display.bands[0].label",
        "A score band's name must be text.",
    ),
    (
        "labels not an object",
        _set(("display",), {"labels": []}),
        "display.labels",
        "The custom wording is not set up correctly.",
    ),
    (
        "unknown label",
        _set(("display",), {"labels": {"subtitle": "Overview"}}),
        "display.labels.subtitle",
        "This wording cannot be changed.",
    ),
    (
        "label not text",
        _set(("display",), {"labels": {"title": 7}}),
        "display.labels.title",
        "Custom wording must be text.",
    ),
    (
        "nesting depth",
        _feedback_fields([_nested_groups(8)]),
        "sections",
        "Questions sit 11 levels deep inside each other; the most allowed is 10. Move some questions out.",
    ),
    (
        "enum values",
        _feedback_fields(
            [{"id": "station", "type": "singleSelect", "options": [f"o{index}" for index in range(1001)]}]
        ),
        "sections",
        "This marking scheme has too many choices (1004; the most allowed is 1000). Remove some choices or "
        "levels.",
    ),
    (
        "name characters",
        _feedback_fields([{"id": "station", "type": "singleSelect", "options": ["x" * 120_001]}]),
        "sections",
        "The names and choices are too long in total (120044 characters; the most allowed is 120000). "
        "Shorten some or remove some.",
    ),
    (
        "marked answers",
        _feedback_fields([{"id": f"note_{index}", "type": "shortText"} for index in range(401)]),
        "sections",
        "The marker would have to give 403 answers; the most allowed is 400. "
        "Remove 3 (use fewer Competencies, or fewer questions per Competency).",
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

    assert {
        "path": "sections",
        "message": (
            "This marking scheme has too many items (5006; the most allowed is 5000). Remove "
            "some Competencies or questions."
        ),
    } in (validate_structure(structure))


def test_fields_that_are_not_a_list_are_refused() -> None:
    structure = copy.deepcopy(VALID)
    structure["sections"][1]["fields"] = {"id": "strengths"}

    assert {
        "path": "sections[1].fields",
        "message": "The questions in this part are not set up correctly. Remove them and add them again.",
    } in validate_structure(structure)


def test_a_structure_that_is_not_an_object_is_refused() -> None:
    assert validate_structure(["not", "a", "rubric"]) == [
        {
            "path": "",
            "message": "This marking scheme could not be read, so it cannot be used. Check it and try again.",
        }
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
        "This Domain uses a rating scale that is not in the marking scheme. Choose one of the scales you "
        "have added.",
    ),
    (
        "rising_points",
        _set(("scales", 0, "levels", 1, "points"), 9),
        "scales[0].levels[1].points",
        "A lower level cannot earn more points than the one above it. List the best level first, for "
        "example Good, then Fair, then Poor.",
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
        "The pass mark uses a level that is not on the rating scale. Choose one of its levels, such as "
        "Good or Fair.",
    ),
    (
        "mixed_scales",
        _second_domain_on_marks,
        "outline[1].scale",
        "Every Domain must use the same rating scale for now. Choose one scale for all of them.",
    ),
    (
        "no_outline",
        _set(("outline",), []),
        "outline",
        "Add at least one Domain, otherwise the marker has nothing to mark.",
    ),
    (
        "every_domain_without_rule",
        _set(("pass",), {"overall": {"score": "labels", "everyDomainPasses": True}}),
        "pass.overall.everyDomainPasses",
        "To require every Domain to pass, set a pass mark for each Domain first.",
    ),
    (
        "bad_kind",
        _set(("competencyFeedback", 0, "kind"), "evidence"),
        "competencyFeedback[0].kind",
        "Choose what kind of feedback this is.",
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
        {
            "path": "rating.points",
            "message": "Give each level on the rating scale its own points, as a number.",
        }
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
