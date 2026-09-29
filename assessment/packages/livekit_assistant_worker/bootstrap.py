"""Fetch the assistant session to run from the backend that dispatched it, and later scene updates."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
from voice_infra import BackendEndpoints
from voice_infra.backend_http import sync_get_json_url, sync_post_json_url
from voice_infra.pacing import PacingPlan

from .metadata import DispatchMetadata
from .modes import ModeProfile, WorkerType, mode_profile


class BootstrapError(RuntimeError):
    def __init__(self, message: str, *, auth_failed: bool = False) -> None:
        super().__init__(message)
        self.auth_failed = auth_failed


TOOL_NAME = re.compile(r"^[a-z][a-z0-9_]{1,63}$")


class RemoteTool(BaseModel):
    """A tool the backend defines and answers; the worker only carries its schema.

    ``parameters`` is the JSON schema the model sees. What the tool does is the
    backend's business: the worker forwards every call and reads back text.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    description: str = Field(min_length=1)
    parameters: dict[str, Any]

    @field_validator("name")
    @classmethod
    def _well_formed_name(cls, value: str) -> str:
        if not TOOL_NAME.match(value):
            raise ValueError(f"tool name {value!r} must match {TOOL_NAME.pattern}")
        return value

    @field_validator("parameters")
    @classmethod
    def _object_schema(cls, value: dict[str, Any]) -> dict[str, Any]:
        if value.get("type") != "object":
            raise ValueError("tool parameters must be a JSON schema of type object")
        return value


class AssistantExtras(BaseModel):
    """What the worker itself decides on: which tools to load, which runtime, and the clock."""

    model_config = ConfigDict(extra="ignore")

    screen_ui_guidance: bool = False
    voice_help_intent: str | None = None
    pacing: PacingPlan | None = None


class GPTLiveInstructions(BaseModel):
    """Instructions for a speech-to-speech session: the voice model, its delegate, and how to open."""

    model_config = ConfigDict(frozen=True)

    voice: str = Field(min_length=1)
    backend: str = Field(min_length=1)
    opening: str = Field(min_length=1)


class AssistantSession(BaseModel):
    """What the worker needs to run one assistant session; every text arrives rendered.

    ``instructions`` is required and, for help sessions, already carries the
    FAQ answers. ``greeting`` is the backend's opening line; without one the
    model generates its own opening. ``gpt_live`` makes speech-to-speech
    possible. ``tools`` are the backend's to define; a mode that loads them
    registers each one and forwards its calls.
    """

    model_config = ConfigDict(extra="ignore")

    session_id: str = Field(min_length=1)
    worker_type: WorkerType
    candidate_ref: str = ""
    instructions: str = Field(min_length=1)
    greeting: str | None = None
    gpt_live: GPTLiveInstructions | None = None
    extras: AssistantExtras = Field(default_factory=AssistantExtras)
    tools: tuple[RemoteTool, ...] = ()

    @field_validator("tools")
    @classmethod
    def _distinct_names(cls, value: tuple[RemoteTool, ...]) -> tuple[RemoteTool, ...]:
        names = [tool.name for tool in value]
        duplicates = sorted({n for n in names if names.count(n) > 1})
        if duplicates:
            raise ValueError(f"tools named more than once: {duplicates}")
        return value

    @property
    def mode(self) -> ModeProfile:
        return mode_profile(self.worker_type)


def parse_bootstrap(payload: Any) -> AssistantSession:
    if not isinstance(payload, dict):
        raise BootstrapError("bootstrap payload must be an object")
    try:
        session = AssistantSession.model_validate(payload.get("session"))
    except Exception as exc:  # noqa: BLE001 — pydantic detail is the message
        raise BootstrapError(f"bootstrap payload is malformed: {exc}") from exc
    if not session.instructions.strip():
        raise BootstrapError(f"{session.worker_type.value} session {session.session_id} arrived without rendered instructions")
    return session


def fetch_bootstrap(endpoints: BackendEndpoints, metadata: DispatchMetadata) -> AssistantSession:
    """Synchronous; callers keep it off the audio loop with ``asyncio.to_thread``."""
    result = sync_get_json_url(
        endpoints.assistant_bootstrap_url(metadata.session_id),
        headers=endpoints.secret_headers(),
        log_prefix="assistant_bootstrap",
    )
    if result.auth_failed:
        raise BootstrapError(f"backend {endpoints.label!r} rejected worker credentials", auth_failed=True)
    if not result.ok or result.data is None:
        raise BootstrapError(f"session {metadata.session_id} unavailable from {endpoints.label!r} (HTTP {result.status})")
    session = parse_bootstrap(result.data)
    if session.session_id != metadata.session_id:
        raise BootstrapError("bootstrap returned a different session than dispatched")
    return session


def fetch_scene_instructions(endpoints: BackendEndpoints, session_id: str, scene: dict[str, Any]) -> str:
    """Instructions for a new scene; the backend renders them from what the browser announced."""
    result = sync_post_json_url(
        endpoints.assistant_scene_url(session_id),
        scene,
        headers=endpoints.secret_headers(),
        log_prefix="assistant_scene",
    )
    instructions = (result.data or {}).get("instructions") if result.ok else None
    if not isinstance(instructions, str) or not instructions.strip():
        raise BootstrapError(f"scene instructions unavailable for session {session_id} (HTTP {result.status})")
    return instructions
