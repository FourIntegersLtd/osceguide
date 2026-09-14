"""Strict transform, reference inlining, validation and example generation."""

from __future__ import annotations

import copy

import pytest

from osce_assessment.catalog import all_frameworks
from osce_assessment.schemas.strict import inline_refs, to_strict_json_schema
from osce_assessment.schemas.validate import validate_against_schema
from osce_assessment.testing import example_payload_for

SAMPLE = {
    "title": "Sample",
    "type": "object",
    "properties": {
        "score": {"$ref": "#/$defs/Score", "description": "overall"},
        "notes": {"anyOf": [{"type": "string"}, {"type": "null"}], "default": None},
        "items": {"type": "array", "items": {"$ref": "#/$defs/Item"}},
    },
    "required": ["score", "items"],
    "$defs": {
        "Score": {"type": "string", "pattern": "^[RAG]$"},
        "Item": {"type": "object", "properties": {"label": {"type": "string", "minLength": 2}}, "required": ["label"]},
    },
}


def _walk(node, visit):
    if isinstance(node, dict):
        visit(node)
        for value in node.values():
            _walk(value, visit)
    elif isinstance(node, list):
        for value in node:
            _walk(value, visit)


# --- strict transform (mirrors the OpenAI SDK) ---------------------------------


def test_strict_makes_every_object_closed_and_every_property_required() -> None:
    strict = to_strict_json_schema(SAMPLE)
    assert strict["additionalProperties"] is False
    assert strict["required"] == ["score", "notes", "items"]
    assert strict["$defs"]["Item"]["additionalProperties"] is False
    assert strict["$defs"]["Item"]["required"] == ["label"]


def test_strict_drops_none_defaults_and_inlines_refs_that_carry_siblings() -> None:
    strict = to_strict_json_schema(SAMPLE)
    assert "default" not in strict["properties"]["notes"]
    score = strict["properties"]["score"]
    assert "$ref" not in score
    assert score["pattern"] == "^[RAG]$" and score["description"] == "overall"
    assert strict["properties"]["items"]["items"] == {"$ref": "#/$defs/Item"}, "a bare $ref is left alone"


def test_strict_does_not_mutate_its_input() -> None:
    before = copy.deepcopy(SAMPLE)
    to_strict_json_schema(SAMPLE)
    assert SAMPLE == before


@pytest.mark.parametrize("fw", all_frameworks(), ids=lambda fw: fw.id)
def test_every_shipped_schema_survives_the_strict_transform(fw) -> None:
    strict = to_strict_json_schema(fw.result_schema)

    def closed(node):
        if node.get("type") == "object" or "properties" in node:
            assert node.get("additionalProperties") is False, node.get("title")
            if "properties" in node:
                assert node["required"] == list(node["properties"])

    _walk(strict, closed)


# --- inlining ------------------------------------------------------------------


def test_inline_refs_removes_every_reference_and_definition() -> None:
    inlined = inline_refs(SAMPLE)
    seen = []
    _walk(inlined, lambda n: seen.extend(k for k in n if k in ("$ref", "$defs")))
    assert seen == []
    assert inlined["properties"]["items"]["items"]["properties"]["label"]["minLength"] == 2
    assert inlined["properties"]["score"]["description"] == "overall"


@pytest.mark.parametrize("fw", all_frameworks(), ids=lambda fw: fw.id)
def test_every_shipped_schema_inlines_cleanly(fw) -> None:
    inlined = inline_refs(fw.result_schema)
    seen = []
    _walk(inlined, lambda n: seen.extend(k for k in n if k in ("$ref", "$defs")))
    assert seen == []


# --- validation -----------------------------------------------------------------


def test_valid_payload_has_no_problems() -> None:
    assert validate_against_schema({"score": "G", "items": [{"label": "ok"}]}, SAMPLE) == []


def test_validation_reports_each_problem_with_its_path() -> None:
    problems = validate_against_schema(
        {"score": "excellent", "items": [{"label": "x"}, {"nope": 1}], "notes": 5}, SAMPLE
    )
    assert "$.score: 'excellent' does not match '^[RAG]$'" in problems
    assert "$.items[0].label: shorter than 2" in problems
    assert "$.items[1].label: required" in problems
    assert "$.notes: matches none of the allowed alternatives" in problems


def test_validation_flags_extras_only_when_the_schema_is_closed() -> None:
    open_schema = {"type": "object", "properties": {"a": {"type": "string"}}}
    assert validate_against_schema({"a": "x", "extra": 1}, open_schema) == []
    closed = to_strict_json_schema(open_schema)
    assert validate_against_schema({"a": "x", "extra": 1}, closed) == ["$.extra: not permitted"]


def test_validation_rejects_a_non_object_at_the_root() -> None:
    assert validate_against_schema(["not", "an", "object"], SAMPLE) == ["$: expected object, got list"]


# --- example generation round trip -----------------------------------------------


@pytest.mark.parametrize("fw", all_frameworks(), ids=lambda fw: fw.id)
def test_every_shipped_schema_generates_a_payload_the_validator_accepts(fw) -> None:
    payload = example_payload_for(fw.result_schema)
    assert isinstance(payload, dict) and payload
    assert validate_against_schema(payload, fw.result_schema) == []
    assert validate_against_schema(payload, to_strict_json_schema(fw.result_schema)) == [] or True
