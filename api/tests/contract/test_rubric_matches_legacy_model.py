"""Each seeded platform rubric asks for exactly what its legacy b2c model asked for.

The oracle is `tests/fixtures/legacy_schemas/b2c/*.json`: the pydantic models
the consumer arm marked with for years. A rubric is now authored data, and the
schema the marker fills is derived from it, so this is the test that the
derivation and the seed together reproduce every field, every description,
every required flag, every nullable and every enum or bound of those models,
for all four exams (plan `docs/plans/rubric-templates.md` §5.2).

Only presentation is normalised away: titles, `$ref` wrapping (both sides are
inlined), and the strict-mode `additionalProperties: false`. Storage metadata
the legacy model carried is dropped from the oracle by `marking_content`,
exactly as the b2b registry dropped it.

Two differences are allowed. By path: SCA's competency rating `score` carries
the R/A/G `enum` where the legacy model had a `^[RAG]$` pattern. An
unconstrained rating would let a marker return "Green" or "B". By hint: the
fields an exam's `seeds/rubric_hints/<exam>.json` lists under `omit` are a
product decision to stop asking for them (SCA's per-domain summaries and
language notes repeated the competency explanations), so they are removed from
the oracle before comparing, and each must still exist in it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.features.rubrics.domain import (
    RubricStructure,
    derive_display_schema,
    derive_result_schema,
    parse_structure,
)
from tests.contract.test_feedback_model_parity import leaf_differences, load, marking_content

API_ROOT = Path(__file__).resolve().parents[2]
SEED = API_ROOT / "seeds" / "platform-starter.json"
HINTS = API_ROOT / "seeds" / "rubric_hints"
EXAMS = ("sca", "plab", "casc", "ortho")


def _inline(node: Any, definitions: dict[str, Any]) -> Any:
    """The schema with every `$ref` replaced by its target; a sibling key wins over the target's."""
    if isinstance(node, dict):
        if "$ref" in node:
            target = _inline(definitions[node["$ref"].split("/")[-1]], definitions)
            siblings = {key: _inline(value, definitions) for key, value in node.items() if key != "$ref"}
            return {**target, **siblings}
        return {key: _inline(value, definitions) for key, value in node.items() if key != "$defs"}
    if isinstance(node, list):
        return [_inline(item, definitions) for item in node]
    return node


def _presentation_free(node: Any) -> Any:
    """Drop titles and the strict-mode wrapping: they change how a schema reads, not what it asks."""
    if isinstance(node, dict):
        return {
            key: _presentation_free(value)
            for key, value in node.items()
            if not (key == "title" and isinstance(value, str))
            and not (key == "additionalProperties" and value is False)
        }
    if isinstance(node, list):
        return [_presentation_free(item) for item in node]
    return node


def normalised(schema: dict[str, Any]) -> dict[str, Any]:
    """A schema reduced to what it asks a marker to fill."""
    content = marking_content(schema)
    return _presentation_free(_inline(content, content.get("$defs", {})))


def without_omitted(schema: dict[str, Any], exam: str) -> dict[str, Any]:
    """The oracle with the hint-omitted fields removed; refuses a path the oracle does not have.

    Deliberately its own walk, not the generator's: this is the check that the
    generator dropped nothing more. It assumes non-nullable parents.
    """
    pruned: dict[str, Any] = json.loads(json.dumps(schema))
    hints = json.loads((HINTS / f"{exam}.json").read_text(encoding="utf-8"))
    for dotted in hints.get("omit") or []:
        *parents, leaf = dotted.split(".")
        node = pruned
        for part in parents:
            node = node["properties"][part]
        assert leaf in node["properties"], f"{exam}: omit names {dotted}, which the legacy model lacks"
        node["properties"].pop(leaf)
        node["required"] = [name for name in node.get("required", []) if name != leaf]
    return pruned


def seeded_structure(exam: str) -> RubricStructure:
    """The parsed structure the seed file authors for one exam."""
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    (entry,) = [row for row in seed["exams"] if row["code"] == exam]
    return parse_structure(entry["rubric"]["structure"])


def competency_rating_paths(structure: RubricStructure) -> set[str]:
    """The leaf path of every competency's rating, where the one allowed difference may sit."""
    return {
        f"/properties/{domain.id}/properties/{competency.id}/properties/{structure.rating.field}/{keyword}"
        for domain in structure.domains
        for competency in domain.competencies
        for keyword in ("enum", "pattern")
    }


def allowed_difference(exam: str, structure: RubricStructure, path: str) -> bool:
    """The named exception: SCA's competency rating, and nothing else."""
    return exam == "sca" and path in competency_rating_paths(structure)


@pytest.mark.parametrize("exam", EXAMS)
def test_the_seeded_rubric_derives_its_legacy_model_exactly(exam: str) -> None:
    structure = seeded_structure(exam)
    derived = normalised(derive_display_schema(structure))
    legacy = without_omitted(normalised(load("b2c", exam)), exam)

    differences = [
        (path, ours, theirs)
        for path, ours, theirs in leaf_differences(derived, legacy)
        if not allowed_difference(exam, structure, path)
    ]

    assert differences == []


def test_the_sca_exception_is_exactly_the_rag_enum_on_competency_ratings() -> None:
    structure = seeded_structure("sca")
    derived = normalised(derive_display_schema(structure))
    legacy = without_omitted(normalised(load("b2c", "sca")), "sca")

    allowed = [
        (path, ours, theirs)
        for path, ours, theirs in leaf_differences(derived, legacy)
        if allowed_difference("sca", structure, path)
    ]

    # 7 global skills + 11 tasks + 11 relating-to-others competencies, each an
    # enum where legacy had a pattern.
    assert len(allowed) == 2 * 29
    for path, ours, theirs in allowed:
        if path.endswith("/enum"):
            assert (ours, theirs) == (["G", "A", "R"], None), path
        else:
            assert (ours, theirs) == (None, "^[RAG]$"), path


def test_sca_priorities_ask_only_for_the_overall_priorities() -> None:
    """The tail of an SCA report is the 2-3 priorities; the per-domain and language notes are gone."""
    structure = seeded_structure("sca")
    (section,) = [part for part in structure.sections if part.id == "actionable_feedback"]
    priorities = derive_result_schema(structure)["properties"]["actionable_feedback"]

    assert section.title == "Priorities"
    assert [spec.id for spec in section.fields] == ["overall_priorities"]
    assert list(priorities["properties"]) == ["overall_priorities"]
    assert priorities["required"] == ["overall_priorities"]


def _drop_system_fields(schema: dict[str, Any], structure: RubricStructure) -> dict[str, Any]:
    """The display schema with every system-written top-level or domain field removed."""
    pruned = json.loads(json.dumps(schema))
    for part in structure.sections:
        for spec in part.fields:
            if spec.source != "system":
                continue
            container = pruned if part.kind == "field" else pruned["properties"][part.id]
            container["properties"].pop(spec.id)
            container["required"] = [name for name in container["required"] if name != spec.id]
    return pruned


@pytest.mark.parametrize("exam", EXAMS)
def test_the_marker_schema_is_the_display_schema_without_system_fields(exam: str) -> None:
    structure = seeded_structure(exam)

    assert derive_result_schema(structure) == _drop_system_fields(derive_display_schema(structure), structure)


def _descriptions(node: Any, path: str = "") -> dict[str, str]:
    """Every description in a normalised schema, by path."""
    found: dict[str, str] = {}
    if isinstance(node, dict):
        if isinstance(node.get("description"), str):
            found[path] = node["description"]
        for key, value in node.items():
            found.update(_descriptions(value, f"{path}/{key}"))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            found.update(_descriptions(item, f"{path}[{index}]"))
    return found


@pytest.mark.parametrize("exam", EXAMS)
def test_every_legacy_description_reaches_the_marker(exam: str) -> None:
    derived = _descriptions(normalised(derive_display_schema(seeded_structure(exam))))
    legacy = _descriptions(without_omitted(normalised(load("b2c", exam)), exam))

    missing = [path for path, text in legacy.items() if text.strip() not in derived.get(path, "")]

    assert legacy
    assert missing == []
