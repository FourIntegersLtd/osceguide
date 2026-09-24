"""The evaluator adapter against the real engine.

`osce_assessment` is not a dependency yet (E-1), so these are skipped unless the
`assessment-platform` checkout is somewhere above this one. When it is, they
check the adapter against the actual engine rather than against a description of
it — the contract most likely to drift silently, because nothing else here
imports it.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.support.rubrics import frozen_rubric


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


def _check_bootstrap(body: dict) -> tuple[object, object]:  # type: ignore[type-arg]
    """Parse a bootstrap body exactly as `livekit_assessment_worker/bootstrap.py` does."""
    from osce_assessment.contracts import AssessmentAttempt, Scenario

    return AssessmentAttempt.model_validate(body["attempt"]), Scenario.model_validate(body["scenario"])


@pytest.mark.db
async def test_a_frozen_bootstrap_parses_as_the_worker_parses_it(client, db_session) -> None:  # type: ignore[no-untyped-def]
    """The half of the contract nothing checked.

    `test_worker_routes` asserted the body had an `attempt` and a `scenario`
    key. It did; the scenario was `{ref, title, raw}`, which the engine's
    `Scenario` rejects on three counts, and no live session could start.
    """
    from tests.contract.test_worker_routes import an_attempt, worker_headers

    attempt_id = await an_attempt(db_session)
    response = await client.get(f"/api/worker/attempts/{attempt_id}", headers=worker_headers())
    assert response.status_code == 200, response.text
    attempt, scenario = _check_bootstrap(response.json())
    assert attempt.definition.evaluation_policy is None  # type: ignore[attr-defined]
    assert scenario.id  # type: ignore[attr-defined]


@pytest.mark.db
async def test_a_rendered_bootstrap_parses_as_the_worker_parses_it(client, db_session, make_actor) -> None:  # type: ignore[no-untyped-def]
    """The real path: a station rendered by the engine, frozen, then handed over."""
    from tests.contract.test_attempt_is_runnable import (
        a_published_library_station,
        an_entitled_candidate,
        worker_headers,
    )
    from tests.support.tokens import bearer

    token = await an_entitled_candidate(db_session, make_actor, "engine-shape@example.com")
    station_version_id = await a_published_library_station(db_session)
    created = await client.post(
        "/api/v1/attempts",
        json={"kind": "practice", "exam_code": "sca", "station_version_id": str(station_version_id)},
        headers=bearer(token),
    )
    assert created.status_code == 201, created.text

    response = await client.get(f"/api/worker/attempts/{created.json()['id']}", headers=worker_headers())
    assert response.status_code == 200, response.text
    attempt, scenario = _check_bootstrap(response.json())
    # The worker picks the patient's voice from these; Raymond is a man.
    assert scenario.patient_gender == "male"  # type: ignore[attr-defined]
    assert attempt.definition.interaction_profile.voice == "male"  # type: ignore[attr-defined]
    assert scenario.title == "Chest pain in a 54-year-old"  # type: ignore[attr-defined]


def test_the_engine_only_needs_pydantic() -> None:
    """The claim ADR 0013 and the plan both rest on.

    If the engine grows an LLM SDK or a database driver, depending on it from
    here stops being cheap and the packaging decision needs revisiting.

    Asked in a fresh interpreter, because `sys.modules` is shared by the whole
    test session: read in-process, this passed alone and failed in a full run,
    and the failure named the engine when the culprit was an unrelated module
    importing an SDK eagerly. A subprocess asks the question the test means.
    """
    probe = (
        "import osce_assessment.contracts.models, sys; "
        "heavy = {'sqlalchemy', 'psycopg', 'fastapi', 'django', 'openai', 'anthropic'}; "
        "print(','.join(sorted(heavy & {n.split('.')[0] for n in sys.modules})))"
    )
    result = subprocess.run(  # noqa: S603 - this interpreter, a literal program
        [sys.executable, "-c", probe], capture_output=True, text=True, check=True
    )
    pulled = result.stdout.strip()
    assert not pulled, f"importing the engine's contracts pulled in {pulled}"


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

    rubric = frozen_rubric()
    adapter = EngineEvaluator(lambda framework: CapturingEngine(), scenario_title="Chest pain")
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
    assert captured["policy"].framework_id == rubric["framework"]["id"]  # type: ignore[union-attr]
    assert captured["policy"].version == "platform-default@1"  # type: ignore[union-attr]
    # The rubric's author wrote the marking instructions; nothing is chosen by id.
    assert captured["policy"].system_prompt_override == rubric["system_prompt"]  # type: ignore[union-attr]
    assert len(captured["transcript"].messages) == 2  # type: ignore[union-attr]
    assert captured["transcript"].complete is True  # type: ignore[union-attr]
    assert captured["attempt"].definition.evaluation_policy is not None  # type: ignore[union-attr]


def test_the_engine_publishes_no_catalogue_to_disagree_with() -> None:
    """This used to assert that four exam rows named four frameworks the engine
    shipped, because an attempt naming any other one could not be marked.

    There is no catalogue to keep in step now: a rubric is authored, its version
    id *is* the framework id, and the whole framework travels with the attempt.
    """
    with pytest.raises(ModuleNotFoundError):
        import osce_assessment.catalog  # noqa: F401


async def test_the_adapter_marks_against_an_authored_rubric_with_no_catalogue() -> None:
    """The point of the whole change: a rubric nobody shipped can be marked with."""
    from osce_assessment.testing import example_payload_for

    from app.features.attempts.evaluator import EngineEvaluator, FrozenFrameworkProvider

    rubric = frozen_rubric()
    framework = FrozenFrameworkProvider(rubric["framework"]).get(rubric["framework"]["id"])

    class Engine:
        def evaluate(self, attempt, transcript, policy, scenario):  # type: ignore[no-untyped-def]
            from osce_assessment.contracts import AssessmentResult

            return AssessmentResult(
                attempt_id="a",
                framework_id=framework.id,
                policy_version=policy.version,
                result=example_payload_for(framework.result_schema),
                provider="primary",
                model="a-model",
                generated_at=datetime.now(UTC),
            )

    adapter = EngineEvaluator(lambda f: Engine())
    payload = await adapter.evaluate(
        rubric=rubric,
        policy_version="platform-default@1",
        transcript=[{"role": "user", "message": "Hi", "seq": 0, "message_id": "m0"}],
    )

    # The marks, not just the metadata. This read `result.payload`, which the
    # engine's model does not define, so every stored result was `{"model_used"}`
    # with the scores silently discarded.
    assert "consulting" in payload
    assert payload["consulting"]["opens_well"]["score"] in {"R", "A", "G"}
    assert payload["model_used"] == "a-model"


def test_a_framework_id_that_is_not_the_frozen_one_is_refused() -> None:
    """There is nothing to resolve against, so a mismatch is a bug, not a lookup."""
    from app.features.attempts.evaluator import FrozenFrameworkProvider

    provider = FrozenFrameworkProvider(frozen_rubric()["framework"])
    with pytest.raises(LookupError):
        provider.get("something-else")


async def test_the_adapter_reports_a_failure_rather_than_an_empty_result() -> None:
    """A model that refuses must not produce a stored result that looks marked."""
    from app.core.ports import EvaluationFailed
    from app.features.attempts.evaluator import EngineEvaluator

    class RefusingEngine:
        def evaluate(self, *args: object, **kwargs: object) -> object:
            raise RuntimeError("model refused")

    adapter = EngineEvaluator(lambda framework: RefusingEngine())
    with pytest.raises(EvaluationFailed):
        await adapter.evaluate(
            rubric=frozen_rubric(),
            policy_version="platform-default@1",
            transcript=[{"role": "user", "message": "Hi", "seq": 0, "message_id": "m0"}],
        )
