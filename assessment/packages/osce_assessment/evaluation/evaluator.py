"""The shared evaluator: one scoring path for every consumer.

The framework supplies the result *shape* as data; the policy supplies the
*scoring* (models, prompt, limits). Provider clients are injected as
factories and used through the smallest surface they share with the real
SDKs, so this module imports no vendor code and the tests use plain fakes.

Primary path: a chat completion constrained by the framework's schema in the
provider's strict structured-output mode. Fallback path: a forced tool call
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
    Scenario,
    Transcript,
)
from ..prompts import UnknownPromptError, default_system_prompt_id, render_user_prompt, system_prompt
from ..schemas.strict import inline_refs, to_strict_json_schema
from ..schemas.validate import validate_against_schema
from .rendering import render_transcript_for_marking

logger = logging.getLogger(__name__)

ClientFactory = Callable[[], Any | None]


class EvaluationError(RuntimeError):
    """The transcript could not be scored. ``attempts`` lists what was tried."""

    def __init__(self, message: str, attempts: list[str] | None = None) -> None:
        super().__init__(message)
        self.attempts = attempts or []


class ProviderError(RuntimeError):
    """One provider call failed; the evaluator may try the next."""


class LLMEvaluator:
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
        if policy.system_prompt_override is not None:
            system = policy.system_prompt_override
        else:
            try:
                system = system_prompt(default_system_prompt_id(framework.id))
            except UnknownPromptError as exc:
                raise EvaluationError(f"no system prompt for framework {framework.id!r}: {exc}") from exc
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
        framework = self._frameworks.get(policy.framework_id)
        if not framework.result_schema:
            raise EvaluationError(f"framework {framework.id!r} has no result schema to score against")
        system, user = self.build_messages(transcript, policy, scenario)
        schema_name = framework.id

        attempts: list[str] = []
        payload: dict[str, Any] | None = None
        provider = model = ""

        primary = self._primary()
        if primary is not None:
            try:
                payload = self._score_primary(primary, policy, framework.result_schema, schema_name, system, user)
                provider, model = "primary", policy.primary_model
            except Exception as exc:  # noqa: BLE001 — recorded, then fall back
                attempts.append(f"primary {policy.primary_model}: {exc}")
                logger.warning("primary scoring failed attempt=%s: %s", attempt.attempt_id, exc)
        else:
            attempts.append("primary: not configured")

        if payload is None and policy.fallback_model and self._fallback is not None:
            fallback = self._fallback()
            if fallback is not None:
                try:
                    payload = self._score_fallback(fallback, policy, framework.result_schema, schema_name, system, user)
                    provider, model = "fallback", policy.fallback_model
                except Exception as exc:  # noqa: BLE001 — recorded
                    attempts.append(f"fallback {policy.fallback_model}: {exc}")
                    logger.error("fallback scoring failed attempt=%s: %s", attempt.attempt_id, exc)
            else:
                attempts.append("fallback: not configured")

        if payload is None:
            raise EvaluationError("no provider produced a result: " + "; ".join(attempts), attempts)

        problems = validate_against_schema(payload, framework.result_schema)
        if problems:
            raise EvaluationError(
                f"{provider} result does not match the {framework.id} schema: " + "; ".join(problems[:10]),
                attempts,
            )

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
    def _score_primary(client: Any, policy: EvaluationPolicy, schema: dict[str, Any], name: str, system: str, user: str) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": policy.primary_model,
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
        if policy.primary_reasoning_effort is not None:
            kwargs["reasoning_effort"] = policy.primary_reasoning_effort
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
    def _score_fallback(client: Any, policy: EvaluationPolicy, schema: dict[str, Any], name: str, system: str, user: str) -> dict[str, Any]:
        response = client.messages.create(
            model=policy.fallback_model,
            max_tokens=policy.fallback_max_tokens,
            temperature=policy.fallback_temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
            tools=[{"name": name, "description": "Record the structured assessment.", "input_schema": inline_refs(schema)}],
            tool_choice={"type": "tool", "name": name},
        )
        for block in getattr(response, "content", []) or []:
            if getattr(block, "type", None) == "tool_use":
                return _as_object(getattr(block, "input", None))
        raise ProviderError("no tool_use block in response")


def _as_object(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProviderError(f"structured output was {type(value).__name__}, not an object")
    return value
