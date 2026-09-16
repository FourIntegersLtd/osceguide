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
        llm_evaluator: Any,
        *,
        scenario_title: str = "",
        examiner_context: str | None = None,
    ) -> None:
        self._evaluator = llm_evaluator
        self._scenario_title = scenario_title
        # Appended verbatim to what the marker sees. Ortho stations carry their
        # expected answers here; everything else leaves it unset.
        self._examiner_context = examiner_context

    async def evaluate(
        self,
        *,
        framework_id: str,
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

        settings = get_settings()
        policy = EvaluationPolicy(
            framework_id=framework_id,
            primary_model=settings.marking_primary_model,
            primary_reasoning_effort=settings.marking_primary_effort,
            fallback_model=settings.marking_fallback_model,
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
            result = self._evaluator.evaluate(attempt, engine_transcript, policy, scenario)
        except Exception as exc:  # noqa: BLE001 - any engine failure is a delivery failure
            log.warning("engine evaluation failed", framework=framework_id, error=str(exc))
            raise EvaluationFailed(str(exc)) from exc

        payload: dict[str, Any] = dict(getattr(result, "payload", {}) or {})
        payload.setdefault("model_used", getattr(result, "model", ""))
        return payload


def build_evaluator() -> Evaluator:
    """Wire the engine, or say plainly that it is not there."""
    try:
        from osce_assessment.catalog import CatalogFrameworkProvider  # noqa: PLC0415
        from osce_assessment.evaluation.evaluator import LLMEvaluator  # noqa: PLC0415
    except ImportError as exc:
        raise EvaluationFailed(
            "The osce_assessment engine is not installed. Run `make engine-dev` "
            "locally, or pin the `engine-vX.Y.Z` tag in pyproject.toml for a "
            "deployment; see docs/OPEN-QUESTIONS.md E-1."
        ) from exc

    from app.features.attempts.llm_clients import (  # noqa: PLC0415
        fallback_client,
        primary_client,
    )

    return EngineEvaluator(
        LLMEvaluator(
            framework_provider=CatalogFrameworkProvider(),
            primary_client=primary_client,
            fallback_client=fallback_client,
        )
    )
