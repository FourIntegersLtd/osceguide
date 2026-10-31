"""The shared evaluator: one scoring path for every consumer.

The framework supplies the result *shape* as data; the policy supplies the
*scoring* (models, prompt, limits). Provider clients are injected as
factories and used through the smallest surface they share with the real
SDKs, so this module imports no vendor code and the tests use plain fakes.

Primary path (``first_provider`` swaps the two): a chat completion constrained by the framework's schema in the
provider's strict structured-output mode. Fallback path: a tool call (asked for, not forced)
whose input schema is the same framework schema, which needs no extra
library. The result payload is checked against the schema before it is
returned, and storage metadata is never part of what the model is asked for.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from ..contracts import (
    AssessmentAttempt,
    AssessmentResult,
    EvaluationPolicy,
    FrameworkProvider,
    InvalidScoreError,
    Scenario,
    Transcript,
    UnknownCompetencyError,
)
from ..prompts import render_user_prompt
from ..schemas.strict import to_strict_json_schema
from ..schemas.tidy import tidy_against_schema
from ..schemas.validate import validate_against_schema
from .anthropic_call import ask_by_tool
from .providers import ClientFactory, ordered_slots
from .rendering import render_transcript_for_marking

logger = logging.getLogger(__name__)


class EvaluationError(RuntimeError):
    """The transcript could not be scored. ``attempts`` lists what was tried."""

    def __init__(self, message: str, attempts: list[str] | None = None) -> None:
        super().__init__(message)
        self.attempts = attempts or []


class ProviderError(RuntimeError):
    """One provider call failed; the evaluator may try the next."""


class LLMEvaluator:
    """Marks a transcript by asking a model for structured output, falling back to a second provider."""

    def __init__(
        self,
        *,
        framework_provider: FrameworkProvider,
        primary_client: ClientFactory,
        fallback_client: ClientFactory | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._frameworks = framework_provider
        self._primary = primary_client
        self._fallback = fallback_client
        self._clock = clock

    # -- prompt assembly -----------------------------------------------------

    def build_messages(self, transcript: Transcript, policy: EvaluationPolicy, scenario: Scenario) -> tuple[str, str]:
        """(system, user) exactly as they will be sent."""
        framework = self._frameworks.get(policy.framework_id)
        # The policy may override, but the framework is expected to carry its
        # own marking instructions. There is no longer a default keyed on the
        # framework id: a rubric nobody wrote a prompt for cannot be marked.
        system = policy.system_prompt_override or framework.system_prompt
        if not system:
            raise EvaluationError(
                f"framework {framework.id!r} carries no system prompt and the policy overrides none"
            )
        user = render_user_prompt(
            station_name=scenario.title,
            transcript=render_transcript_for_marking(transcript),
        )
        if scenario.examiner_context:
            user += scenario.examiner_context
        return system, user

    # -- scoring -------------------------------------------------------------

    def evaluate(
        self,
        attempt: AssessmentAttempt,
        transcript: Transcript,
        policy: EvaluationPolicy,
        scenario: Scenario,
    ) -> AssessmentResult:
        """Mark the transcript against the policy's framework and return the validated result."""
        framework = self._frameworks.get(policy.framework_id)
        if not framework.result_schema:
            raise EvaluationError(f"framework {framework.id!r} has no result schema to score against")
        system, user = self.build_messages(transcript, policy, scenario)
        schema_name = framework.id

        attempts: list[str] = []
        payload: dict[str, Any] | None = None
        provider = model = ""

        for slot in ordered_slots(policy, openai=self._primary, anthropic=self._fallback):
            if payload is not None or not slot.configured:
                continue
            client = slot.factory()  # type: ignore[misc]
            if client is None:
                attempts.append(f"{slot.label}: not configured")
                continue
            score = self._score_openai if slot.provider == "openai" else self._score_anthropic
            try:
                payload = score(client, policy, framework.result_schema, schema_name, system, user, slot.label, attempts)
                provider, model = slot.label, slot.model or ""
            except Exception as exc:  # noqa: BLE001 — recorded, then the next provider
                attempts.append(f"{slot.label} {slot.model}: {exc}")
                log = logger.warning if slot.label == "primary" else logger.error
                log("%s scoring failed attempt=%s: %s", slot.label, attempt.attempt_id, exc)

        if payload is None:
            raise EvaluationError("no provider produced a result: " + "; ".join(attempts), attempts)

        payload = tidy_against_schema(payload, framework.result_schema)
        problems = validate_against_schema(payload, framework.result_schema)
        if problems:
            raise EvaluationError(
                f"{provider} result does not match the {framework.id} schema: " + "; ".join(problems[:10]),
                attempts,
            )
        # The schema checks shape; it does not hold a model to a rating's
        # native range (the validator does not check minimum or maximum). A framework
        # that names its rating field is checked here too.
        if framework.rating_field:
            try:
                framework.validate_scores(framework.scores_in(payload))
            except (UnknownCompetencyError, InvalidScoreError) as exc:
                raise EvaluationError(f"{provider} result: {exc}", attempts) from exc

        return AssessmentResult(
            attempt_id=attempt.attempt_id,
            framework_id=framework.id,
            policy_version=policy.version,
            result=payload,
            provider=provider,
            model=model,
            generated_at=self._clock(),
            raw_metadata={
                "fallback_used": provider == "fallback",
                "attempts": attempts,
                "framework_version": framework.version,
            },
        )

    # -- provider calls ------------------------------------------------------

    @staticmethod
    def _score_openai(
        client: Any, policy: EvaluationPolicy, schema: dict[str, Any], name: str, system: str, user: str, *_: Any
    ) -> dict[str, Any]:
        """Ask the OpenAI slot for a JSON object matching the schema."""
        kwargs: dict[str, Any] = {
            "model": policy.openai_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": name, "schema": to_strict_json_schema(schema), "strict": True},
            },
            "timeout": policy.timeout_s,
        }
        if policy.openai_reasoning_effort is not None:
            kwargs["reasoning_effort"] = policy.openai_reasoning_effort
        response = client.chat.completions.create(**kwargs)
        message = response.choices[0].message
        refusal = getattr(message, "refusal", None)
        if refusal:
            raise ProviderError(f"refused: {refusal}")
        content = getattr(message, "content", None)
        if not content:
            raise ProviderError("empty response")
        return _as_object(json.loads(content))

    @staticmethod
    def _score_anthropic(
        client: Any, policy: EvaluationPolicy, schema: dict[str, Any], name: str, system: str, user: str,
        label: str, attempts: list[str],
    ) -> dict[str, Any]:
        """Ask the Anthropic slot for the same object through a recording tool it is told to call.

        Without a forced tool call claude-sonnet-5-5 sometimes nests a field as a string or lifts it
        to the top level, so a reply that misses the schema is answered with its own errors, twice.
        """
        value, corrections = ask_by_tool(
            client, policy, schema=schema, name=name, description="Record the structured assessment.",
            system=system, user=user, error=ProviderError,
            check=lambda payload: validate_against_schema(tidy_against_schema(payload, schema), schema),
        )
        attempts.extend(f"{label} {policy.anthropic_model}: corrected after {note}" for note in corrections)
        return value


def _as_object(value: Any) -> dict[str, Any]:
    """Return the value if it is a JSON object, otherwise raise a provider error."""
    if not isinstance(value, dict):
        raise ProviderError(f"structured output was {type(value).__name__}, not an object")
    return value
