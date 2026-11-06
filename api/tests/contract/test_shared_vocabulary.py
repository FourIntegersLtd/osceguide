"""The word lists that api, the marking engine and the web app each hold a copy of still agree.

A rubric field's role, a rating's kind and the kinds of study material are
written down once per codebase: Python here, Python in the engine, TypeScript
in the browser. Nothing shares them at run time, so a value added on one side
was found by a person, on a screen that silently ignored it. These tests read
every copy and compare them, so the mismatch is found here instead.

When one fails, the fix is to make the same change in each file it names.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import get_args

import pytest
from osce_assessment.contracts import rating as engine_rating
from osce_assessment.prompts import dashboard_tutor as engine_tutor

from app.features.assistant.content.request import TOPIC_KINDS
from app.features.rubrics import validation
from app.features.tutor_memory import domain as tutor_domain
from app.features.tutor_memory.tools_catalog import TOOL_ROLES

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
WEB_BUILDER_VOCABULARY = REPOSITORY_ROOT / "web/src/capabilities/authoring/rubrics/schemeModel.ts"
WEB_FEEDBACK_VIEW = REPOSITORY_ROOT / "web/src/capabilities/feedback/rubricView.ts"


def typescript_union(path: Path, type_name: str) -> tuple[str, ...]:
    """The string members of `export type <type_name> = "a" | "b";` in a TypeScript file, in order."""
    declaration = re.search(rf"export type {type_name}\s*=([^;]+);", path.read_text(encoding="utf-8"))
    assert declaration is not None, f"{path.name} no longer declares the type {type_name}"
    return tuple(re.findall(r'"([^"]+)"', declaration.group(1)))


def test_the_engine_knows_every_field_role_the_api_accepts() -> None:
    assert get_args(engine_rating.FieldRole) == validation.FIELD_ROLES


def test_the_engine_knows_every_rating_kind_the_api_accepts() -> None:
    assert get_args(engine_rating.Rating.model_fields["kind"].annotation) == validation.RATING_KINDS


@pytest.mark.parametrize(
    ("type_name", "expected"),
    [
        ("BlockKind", validation.BLOCK_KINDS),
        ("FeedbackKind", validation.FEEDBACK_KINDS),
        ("FeedbackShape", validation.FEEDBACK_SHAPES),
        ("ScoreKind", validation.SCORE_KINDS),
        ("RuleType", validation.RULE_TYPES),
        ("ScaleStep", validation.SCALE_STEPS),
        ("ShowKey", validation.SCHEME_SHOW),
    ],
)
def test_the_rubric_builder_offers_exactly_what_the_api_accepts(
    type_name: str, expected: tuple[str, ...]
) -> None:
    assert typescript_union(WEB_BUILDER_VOCABULARY, type_name) == expected


@pytest.mark.parametrize(
    ("type_name", "expected"),
    [("FieldRole", validation.FIELD_ROLES), ("FieldType", validation.FIELD_TYPES)],
)
def test_the_feedback_screen_reads_exactly_what_the_api_stores(
    type_name: str, expected: tuple[str, ...]
) -> None:
    assert typescript_union(WEB_FEEDBACK_VIEW, type_name) == expected


def test_the_tutor_prompt_and_the_api_name_the_same_tool_roles() -> None:
    assert tuple(TOOL_ROLES) == engine_tutor.TOOL_ROLES


def test_a_topic_may_be_any_kind_of_study_material_and_nothing_else() -> None:
    assert TOPIC_KINDS == tutor_domain.MEDIA_KINDS


@pytest.mark.parametrize("kind", TOPIC_KINDS)
def test_the_tutor_prompt_can_say_where_each_kind_of_topic_was_read(kind: str) -> None:
    brief = {"topic": {"kind": kind, "title": "Asthma"}}
    assert engine_tutor._topic_source(brief, engine_tutor.DEFAULT_LABELS) != ""
