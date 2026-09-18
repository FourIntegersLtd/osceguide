"""Oracle: `b2b-api/tests/test_feedback_parity_with_b2c.py`.

Both legacy backends carried their own copy of the same four marking schemas
and the same prompts, and nothing compared them until that test existed. It
found two real divergences, and this file carries them forward — because this
platform replaces both arms with **one** marking path, so "which of the two did
we keep, and does the other arm's marking change?" is now a question somebody
has to be able to answer.

The snapshots in `tests/fixtures/legacy_schemas/` are the oracle. They are
committed here rather than read from the sibling checkouts on purpose: those
repositories are being decommissioned, and the legacy test skipped itself when
they were absent, which would have quietly turned this into no test at all.

What was true at capture (2026-09-17), asserted below:
  * PLAB and Ortho are byte-identical between the two arms.
  * b2c registers the *Extended* SCA and CASC models, adding storage metadata
    the language model is asked to fill and the backend then discards, plus
    `live_coverage` on SCA — what the live panel showed as the consultation
    ran, which the exam arm deliberately never shows.
  * With that metadata removed, CASC is identical and SCA differs in exactly
    one field description: b2b tells the model to refer to the candidate as
    "the doctor", and spells "behaviours" where b2c spells "behaviors".
  * The three system prompts are byte-identical. The shared user prompt has one
    sentence in a different position.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
SCHEMAS = FIXTURES / "legacy_schemas"
PROMPTS = FIXTURES / "legacy_prompts"

# Oracle: `b2b-api/app/features/feedback/ai/registry._METADATA_FIELDS`. Fields
# the schema carries for storage rather than for marking.
METADATA_FIELDS = frozenset(
    {
        "feedback_id",
        "user_id",
        "mock_id",
        "station_id",
        "created_at",
        "updated_at",
        "evaluated_by",
        "attempt_id",
        "likes",
        "liked_by",
        "live_coverage",
    }
)


def load(arm: str, exam: str) -> dict[str, Any]:
    return json.loads((SCHEMAS / arm / f"{exam}.json").read_text(encoding="utf-8"))


def reachable_defs(schema: dict[str, Any]) -> set[str]:
    """Names in `$defs` still referenced, directly or through another definition."""
    defs = schema.get("$defs", {})
    reachable: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/$defs/"):
                name = ref.split("/")[-1]
                if name not in reachable:
                    reachable.add(name)
                    walk(defs.get(name))
            for key, value in node.items():
                if key != "$ref":
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk({k: v for k, v in schema.items() if k != "$defs"})
    return reachable


def marking_content(schema: dict[str, Any]) -> dict[str, Any]:
    """What the schema asks the model to judge, with storage stripped out.

    Removing a property can orphan the `$defs` entry only it referenced, so the
    definitions are pruned to what the remaining schema still reaches —
    otherwise a metadata field carrying its own nested model reads as marking
    drift when it is nothing of the kind.
    """
    stripped = json.loads(json.dumps(schema))
    stripped.pop("title", None)
    for name in METADATA_FIELDS:
        stripped.get("properties", {}).pop(name, None)
    if "required" in stripped:
        stripped["required"] = [r for r in stripped["required"] if r not in METADATA_FIELDS]
    if "$defs" in stripped:
        keep = reachable_defs(stripped)
        stripped["$defs"] = {k: v for k, v in stripped["$defs"].items() if k in keep}
    return stripped


def leaf_differences(a: Any, b: Any, path: str = "") -> list[tuple[str, Any, Any]]:
    """Every leaf the two disagree on, by path. A diff, not a boolean."""
    if isinstance(a, dict) and isinstance(b, dict):
        out: list[tuple[str, Any, Any]] = []
        for key in sorted(set(a) | set(b)):
            out.extend(leaf_differences(a.get(key), b.get(key), f"{path}/{key}"))
        return out
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        out = []
        for index, (x, y) in enumerate(zip(a, b, strict=True)):
            out.extend(leaf_differences(x, y, f"{path}[{index}]"))
        return out
    return [] if a == b else [(path, a, b)]


def test_the_snapshots_were_captured() -> None:
    """Without this the whole file passes vacuously once somebody moves a directory."""
    for arm in ("b2b", "b2c"):
        for exam in ("sca", "casc", "plab", "ortho"):
            assert (SCHEMAS / arm / f"{exam}.json").exists(), f"{arm}/{exam}.json is missing"
    assert len(list(PROMPTS.glob("*.txt"))) == 8


@pytest.mark.parametrize("exam", ["plab", "ortho"])
def test_plab_and_ortho_marked_identically_in_both_arms(exam: str) -> None:
    """Byte-identical, so unifying them costs nothing and changes nothing."""
    assert (SCHEMAS / "b2c" / f"{exam}.json").read_bytes() == (SCHEMAS / "b2b" / f"{exam}.json").read_bytes()


@pytest.mark.parametrize(
    ("exam", "consumer_title", "exam_arm_title"),
    [
        ("sca", "ExtendedScaFeedbackResponseModel", "ScaFeedbackResponseModel"),
        ("casc", "ExtendedCascFeedbackResponseModel", "CascFeedbackResponseModel"),
    ],
)
def test_the_consumer_arm_asked_the_model_for_storage_it_then_discarded(
    exam: str, consumer_title: str, exam_arm_title: str
) -> None:
    """b2c made the marking model fill in `feedback_id` and `created_at`.

    Worth pinning rather than shrugging at: every field in the schema is a
    field the model spends attention on, and these ones were thrown away.
    """
    consumer, exam_arm = load("b2c", exam), load("b2b", exam)
    assert consumer["title"] == consumer_title
    assert exam_arm["title"] == exam_arm_title

    extra = set(consumer["properties"]) - set(exam_arm["properties"])
    assert extra, "expected the Extended model to add fields"
    assert extra <= METADATA_FIELDS, f"non-metadata fields only in the consumer arm: {extra}"
    assert not set(exam_arm["properties"]) - set(consumer["properties"])


def test_casc_marking_content_was_identical_once_storage_is_removed() -> None:
    assert leaf_differences(marking_content(load("b2c", "casc")), marking_content(load("b2b", "casc"))) == []


def test_sca_differed_in_exactly_one_field_description() -> None:
    """The one real SCA drift, pinned so whoever resolves it does so deliberately.

    Both halves matter. "The doctor" is what the transcript tags the candidate
    as, so the arm without that sentence is asking a model to judge somebody it
    has not been told how to refer to; and one arm spells the rubric's language
    in British English while the other does not.
    """
    differences = leaf_differences(marking_content(load("b2c", "sca")), marking_content(load("b2b", "sca")))
    assert differences, "the two SCA schemas have converged; delete this test and its note"

    paths = {path for path, _, _ in differences}
    assert all(path.endswith("/score_explanation/description") for path in paths), paths

    for _, consumer_text, exam_arm_text in differences:
        assert 'Refer to the GP trainee as "the doctor"' in exam_arm_text
        assert 'Refer to the GP trainee as "the doctor"' not in consumer_text
        assert "behaviours" in exam_arm_text and "behaviors" in consumer_text


@pytest.mark.parametrize("exam", ["sca", "plab", "ortho"])
def test_the_system_prompts_were_byte_identical(exam: str) -> None:
    consumer = (PROMPTS / f"b2c_{exam}_system.txt").read_text(encoding="utf-8")
    exam_arm = (PROMPTS / f"b2b_{exam}_system.txt").read_text(encoding="utf-8")
    assert consumer == exam_arm


def test_the_user_prompt_had_the_same_sentences_in_a_different_order() -> None:
    """One sentence, moved. Enough to change what a model attends to first."""
    consumer = (PROMPTS / "b2c_user_evaluation.txt").read_text(encoding="utf-8")
    exam_arm = (PROMPTS / "b2b_user_evaluation.txt").read_text(encoding="utf-8")

    def lines(text: str) -> list[str]:
        return [line.strip() for line in text.strip().splitlines() if line.strip()]

    assert consumer != exam_arm, "the user prompts have converged; delete this test and its note"
    assert sorted(lines(consumer)) == sorted(lines(exam_arm))
    moved = (
        "Transcript speakers are tagged DOCTOR (GP trainee under assessment) and PATIENT (simulated patient)."
    )
    assert lines(exam_arm).index(moved) < lines(consumer).index(moved)
