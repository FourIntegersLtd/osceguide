"""Fetch the attempt to run from the backend that dispatched it."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from osce_assessment.contracts import AssessmentAttempt, Scenario
from voice_infra import BackendEndpoints
from voice_infra.backend_http import sync_get_json

from .metadata import DispatchMetadata

logger = logging.getLogger(__name__)


class BootstrapError(RuntimeError):
    """The attempt could not be fetched or is malformed."""

    def __init__(self, message: str, *, auth_failed: bool = False) -> None:
        super().__init__(message)
        self.auth_failed = auth_failed


@dataclass(frozen=True)
class Bootstrap:
    attempt: AssessmentAttempt
    scenario: Scenario


def parse_bootstrap(payload: Any) -> Bootstrap:
    """``{"attempt": <AssessmentAttempt>, "scenario": <Scenario>}``.

    The attempt's interaction profile must already carry rendered instructions:
    this worker holds no templates and no knowledge of scenario shapes.
    """
    if not isinstance(payload, dict):
        raise BootstrapError("bootstrap payload must be an object")
    try:
        attempt = AssessmentAttempt.model_validate(payload.get("attempt"))
        scenario = Scenario.model_validate(payload.get("scenario"))
    except Exception as exc:  # noqa: BLE001 — pydantic detail is the message
        raise BootstrapError(f"bootstrap payload is malformed: {exc}") from exc
    if not attempt.definition.interaction_profile.instructions.strip():
        raise BootstrapError(f"attempt {attempt.attempt_id} has no rendered instructions")
    return Bootstrap(attempt=attempt, scenario=scenario)


def fetch_bootstrap(endpoints: BackendEndpoints, metadata: DispatchMetadata) -> Bootstrap:
    """Synchronous; callers keep it off the audio loop with ``asyncio.to_thread``."""
    result = sync_get_json(
        endpoints.required_base_url(),
        metadata.bootstrap_path,
        headers=endpoints.secret_headers(),
        log_prefix="bootstrap",
    )
    if result.auth_failed:
        raise BootstrapError(f"backend {endpoints.label!r} rejected worker credentials", auth_failed=True)
    if not result.ok or result.data is None:
        raise BootstrapError(f"attempt {metadata.attempt_id} unavailable from {endpoints.label!r} (HTTP {result.status})")
    bootstrap = parse_bootstrap(result.data)
    if bootstrap.attempt.attempt_id != metadata.attempt_id:
        raise BootstrapError("bootstrap returned a different attempt than dispatched")
    return bootstrap
