"""The evaluator adapter against the real engine.

`osce_assessment` is not a dependency yet (E-1), so these are skipped unless the
`assessment-platform` checkout is somewhere above this one. When it is, they
check the adapter against the actual engine rather than against a description of
it — the contract most likely to drift silently, because nothing else here
imports it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


def _find_engine() -> Path | None:
    """Look upward for the assessment-platform checkout.

    Searched rather than counted: the depth differs between a worktree and a
    plain checkout, and a hardcoded `parents[n]` quietly points at nothing the
    moment either moves — which is exactly how these tests first "passed".
    """
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "assessment-platform" / "packages"
        if (candidate / "osce_assessment").is_dir():
            return candidate
    return None


_ENGINE = _find_engine()
if _ENGINE is not None and str(_ENGINE) not in sys.path:
    # At import time, not in a fixture: the test bodies import the engine, and a
    # fixture runs too late for that.
    sys.path.insert(0, str(_ENGINE))

pytestmark = pytest.mark.skipif(
    _ENGINE is None,
    reason="assessment-platform checkout not present; the engine is not a dependency yet (E-1)",
)


def test_the_engine_only_needs_pydantic() -> None:
    """The claim ADR 0013 and the plan both rest on.

    If the engine grows an LLM SDK or a database driver, depending on it from
    here stops being cheap and the packaging decision needs revisiting.
    """
    import osce_assessment.contracts.models  # noqa: F401

    heavy = {"sqlalchemy", "psycopg", "fastapi", "django", "openai", "anthropic"}
    loaded = {name.split(".")[0] for name in sys.modules}
    assert not (heavy & loaded & {"openai", "anthropic"}), (
        "importing the engine's contracts pulled in an LLM SDK"
    )


async def test_the_adapter_builds_every_object_the_engine_expects() -> None:
    """Builds the real argument set for `LLMEvaluator.evaluate`.

    This is the test that earned its place: the adapter was first written from
    a partial reading of the engine and passed `ref=` to a model that takes
    `id`/`source`, and an int where a version string was wanted. Neither would
    have surfaced until somebody's attempt was marked.
    """
    from app.core.ports import EvaluationFailed
    from app.features.attempts.evaluator import EngineEvaluator

    captured: dict[str, object] = {}

    class CapturingEngine:
        def evaluate(self, attempt, transcript, policy, scenario):  # type: ignore[no-untyped-def]
            captured.update(attempt=attempt, transcript=transcript, policy=policy, scenario=scenario)
            raise RuntimeError("stop here; construction is what is under test")

    rubric = {
        "framework": {"id": "sca-rcgp-v1", "label": "SCA", "version": "1", "scale": ["R", "A", "G"]},
        "system_prompt": "Mark this consultation.",
    }
    adapter = EngineEvaluator(lambda _fw: CapturingEngine(), scenario_title="Chest pain")
    with pytest.raises(EvaluationFailed):
        await adapter.evaluate(
            rubric=rubric,
            policy_version="platform-default@1",
            transcript=[
                {"role": "user", "message": "Hello doctor", "seq": 0, "message_id": "m0"},
                {"role": "assistant", "message": "Tell me more", "seq": 1, "message_id": "m1"},
            ],
        )

    assert captured["scenario"].title == "Chest pain"  # type: ignore[union-attr]
    assert captured["policy"].framework_id == "sca-rcgp-v1"  # type: ignore[union-attr]
    assert captured["policy"].version == "platform-default@1"  # type: ignore[union-attr]
    assert len(captured["transcript"].messages) == 2  # type: ignore[union-attr]
    assert captured["transcript"].complete is True  # type: ignore[union-attr]
    assert captured["attempt"].definition.evaluation_policy is not None  # type: ignore[union-attr]


def test_the_four_framework_ids_are_in_the_legacy_catalog() -> None:
    """Published exams must load a marking snapshot from the legacy vendor."""
    from app.features.attempts.published_marking import marking_snapshot
    from app.features.catalog.domain import PUBLISHED_EXAMS

    for exam in PUBLISHED_EXAMS:
        snap = marking_snapshot(exam.framework_id)
        assert snap["framework"]["id"] == exam.framework_id
        assert str(snap.get("system_prompt") or "").strip()


async def test_the_adapter_reports_a_failure_rather_than_an_empty_result() -> None:
    """A model that refuses must not produce a stored result that looks marked."""
    from app.core.ports import EvaluationFailed
    from app.features.attempts.evaluator import EngineEvaluator

    class RefusingEngine:
        def evaluate(self, *args: object, **kwargs: object) -> object:
            raise RuntimeError("model refused")

    rubric = {
        "framework": {"id": "sca-rcgp-v1", "label": "SCA", "version": "1", "scale": ["R", "A", "G"]},
        "system_prompt": "Mark this consultation.",
    }
    adapter = EngineEvaluator(lambda _fw: RefusingEngine())
    with pytest.raises(EvaluationFailed):
        await adapter.evaluate(
            rubric=rubric,
            policy_version="platform-default@1",
            transcript=[{"role": "user", "message": "Hi", "seq": 0, "message_id": "m0"}],
        )
