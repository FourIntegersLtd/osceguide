"""The engine adapter behind `core.ports.Evaluator`.

`osce_assessment.LLMEvaluator` takes engine contract objects and returns an
`AssessmentResult`; the port speaks dicts. This translates between them, which
is the whole job — the marking itself belongs to the engine and nothing here
should ever reimplement a piece of it.

The engine is imported lazily so the API starts, and the rest of the tests run,
without it installed — `make engine-dev` puts it there from the sibling
checkout. When it is genuinely absent `build_evaluator` raises rather than
guessing: a deployment that tries to mark without an engine should say so
instead of storing an empty result.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.core.logging import get_logger
from app.core.ports import EvaluationFailed, Evaluator
from app.core.settings import get_settings

log = get_logger(__name__)


def _as_int(value: object, default: int) -> int:
    """Turns arrive as loosely typed dicts from the database."""
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


class EngineEvaluator:
    """Marks a transcript with `osce_assessment`.

    Holds no marking logic of its own. If this file ever grows a rule about
    what a good answer looks like, the boundary has been crossed.
    """

    def __init__(
        self,
        build: Any,
        *,
        scenario_title: str = "",
        examiner_context: str | None = None,
    ) -> None:
        # A factory rather than an evaluator: each marking builds one around the
        # rubric frozen onto that attempt, so two attempts marked in the same
        # process cannot be scored against each other's rubric.
        self._build = build
        self._scenario_title = scenario_title
        # Appended verbatim to what the marker sees: the expected answers a
        # station template marks `examiner`, which the candidate never heard.
        self._examiner_context = examiner_context

    async def evaluate(
        self,
        *,
        rubric: dict[str, object],
        policy_version: str,
        transcript: list[dict[str, object]],
    ) -> dict[str, object]:
        from osce_assessment.contracts.models import (  # noqa: PLC0415
            AIInteractionProfile,
            AssessmentAttempt,
            AssessmentDefinition,
            EvaluationPolicy,
            InteractionMode,
            MessageRole,
            Scenario,
            ScenarioRef,
            ScenarioSource,
            Transcript,
            TranscriptMessage,
        )

        raw_framework = rubric.get("framework")
        framework = dict(raw_framework) if isinstance(raw_framework, dict) else {}
        framework_id = str(framework.get("id") or "")
        if not framework_id:
            raise EvaluationFailed("The attempt carries no rubric, so there is nothing to mark against.")

        settings = get_settings()
        policy = EvaluationPolicy(
            framework_id=framework_id,
            primary_model=settings.marking_primary_model,
            primary_reasoning_effort=settings.marking_primary_effort,
            fallback_model=settings.marking_fallback_model,
            # The marking instructions the rubric's author wrote. The engine
            # ships none to fall back on, which is the point: nothing is chosen
            # by framework id any more.
            system_prompt_override=str(rubric.get("system_prompt") or "") or None,
            version=policy_version,
        )
        scenario_ref = ScenarioRef(source=ScenarioSource.INLINE, scenario_id="scored")
        scenario = Scenario(
            id="scored",
            source=ScenarioSource.INLINE,
            title=self._scenario_title or "Station",
            examiner_context=self._examiner_context,
        )
        # The interaction is over by the time anything is marked, so the profile
        # is a formality the model requires and the evaluator never reads.
        definition = AssessmentDefinition(
            id=policy_version,
            version=policy_version,
            framework_id=framework_id,
            scenario_ref=scenario_ref,
            interaction_profile=AIInteractionProfile(mode=InteractionMode.PATIENT),
            evaluation_policy=policy,
            snapshot_at=datetime.now(UTC),
        )
        attempt = AssessmentAttempt(attempt_id=policy_version, definition=definition, candidate_ref="")
        engine_transcript = Transcript(
            attempt_id=attempt.attempt_id,
            messages=tuple(
                TranscriptMessage(
                    role=MessageRole(str(turn.get("role", "user"))),
                    message=str(turn.get("message", "")),
                    timestamp=datetime.now(UTC),
                    message_id=str(turn.get("message_id", index)),
                    seq=_as_int(turn.get("seq"), index),
                )
                for index, turn in enumerate(transcript)
            ),
            complete=True,
        )

        try:
            engine_result = self._build(framework).evaluate(attempt, engine_transcript, policy, scenario)
        except Exception as exc:  # noqa: BLE001 - any engine failure is a delivery failure
            log.warning("engine evaluation failed", framework=framework_id, error=str(exc))
            raise EvaluationFailed(str(exc)) from exc

        # `AssessmentResult.result` holds the marks. This read `result.payload`,
        # which the model does not define and `extra="forbid"` cannot add, so
        # `getattr` returned the default and every stored result was
        # `{"model_used": ...}` with the scores silently discarded.
        payload: dict[str, Any] = dict(engine_result.result or {})
        payload.setdefault("model_used", getattr(engine_result, "model", ""))
        return payload


class FrozenFrameworkProvider:
    """Serves exactly one framework: the one frozen onto the attempt.

    This resolves nothing: the rubric arrived with the attempt, and an id that is not it is a bug
    worth hearing about rather than a lookup worth attempting.
    """

    def __init__(self, framework: dict[str, Any]) -> None:
        from osce_assessment.contracts import CompetencyFramework  # noqa: PLC0415

        self._framework = CompetencyFramework.model_validate(framework)

    def get(self, framework_id: str) -> Any:
        if framework_id != self._framework.id:
            raise LookupError(
                f"This attempt was frozen against framework {self._framework.id!r}, not {framework_id!r}."
            )
        return self._framework


def build_evaluator() -> Evaluator:
    """Wire the engine, or say plainly that it is not there."""
    try:
        from osce_assessment.evaluation.evaluator import LLMEvaluator  # noqa: PLC0415
    except ImportError as exc:
        raise EvaluationFailed(
            "The osce_assessment engine is not installed. Run `make engine-dev` "
            "locally, or pin the `engine-vX.Y.Z` tag in pyproject.toml for a "
            "deployment."
        ) from exc

    from app.features.attempts.llm_clients import (  # noqa: PLC0415
        fallback_client,
        primary_client,
    )

    def build(framework: dict[str, Any]) -> Any:
        return LLMEvaluator(
            framework_provider=FrozenFrameworkProvider(framework),
            primary_client=primary_client,
            fallback_client=fallback_client,
        )

    return EngineEvaluator(build)
