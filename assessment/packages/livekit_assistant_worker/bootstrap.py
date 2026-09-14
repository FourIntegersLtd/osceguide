"""Fetch the assistant session to run from the backend that dispatched it."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from voice_infra import BackendEndpoints
from voice_infra.backend_http import sync_get_json

from .metadata import DispatchMetadata

WorkerType = Literal["help", "onboarding", "dashboard", "athena-doctor"]
SUPPORTED_WORKER_TYPES: tuple[str, ...] = ("help", "onboarding", "dashboard", "athena-doctor")


class BootstrapError(RuntimeError):
    def __init__(self, message: str, *, auth_failed: bool = False) -> None:
        super().__init__(message)
        self.auth_failed = auth_failed


class AssistantExtras(BaseModel):
    model_config = ConfigDict(extra="ignore")

    screen_ui_guidance: bool = False
    voice_help_intent: str | None = None
    onboarding_question: str | None = None
    patient_line: str | None = None
    onboarding_phase: str = "demo"
    user_name: str = ""


class AssistantSession(BaseModel):
    """What the worker needs to run one assistant session.

    ``instructions`` is the backend-rendered text for data-dependent modes
    (dashboard, athena-doctor). Help and onboarding render from the worker's
    own templates and leave it empty.
    """

    model_config = ConfigDict(extra="ignore")

    session_id: str = Field(min_length=1)
    worker_type: WorkerType
    candidate_ref: str = ""
    instructions: str | None = None
    greeting: str | None = None
    extras: AssistantExtras = Field(default_factory=AssistantExtras)


def parse_bootstrap(payload: Any) -> AssistantSession:
    if not isinstance(payload, dict):
        raise BootstrapError("bootstrap payload must be an object")
    try:
        return AssistantSession.model_validate(payload.get("session"))
    except Exception as exc:  # noqa: BLE001 — pydantic detail is the message
        raise BootstrapError(f"bootstrap payload is malformed: {exc}") from exc


def fetch_bootstrap(endpoints: BackendEndpoints, metadata: DispatchMetadata) -> AssistantSession:
    """Synchronous; callers keep it off the audio loop with ``asyncio.to_thread``."""
    result = sync_get_json(endpoints.required_base_url(), metadata.bootstrap_path, headers=endpoints.secret_headers(), log_prefix="assistant_bootstrap")
    if result.auth_failed:
        raise BootstrapError(f"backend {endpoints.label!r} rejected worker credentials", auth_failed=True)
    if not result.ok or result.data is None:
        raise BootstrapError(f"session {metadata.session_id} unavailable from {endpoints.label!r} (HTTP {result.status})")
    session = parse_bootstrap(result.data)
    if session.session_id != metadata.session_id:
        raise BootstrapError("bootstrap returned a different session than dispatched")
    return session
