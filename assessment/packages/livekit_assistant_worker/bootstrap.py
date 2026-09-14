"""Fetch the assistant session to run from the backend that dispatched it, and later scene updates."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from voice_infra import BackendEndpoints
from voice_infra.backend_http import sync_get_json, sync_post_json

from .help_corpus import HelpCorpus
from .metadata import SCENE_PATH_TEMPLATE, DispatchMetadata
from .modes import ModeProfile, WorkerType, mode_profile


class BootstrapError(RuntimeError):
    def __init__(self, message: str, *, auth_failed: bool = False) -> None:
        super().__init__(message)
        self.auth_failed = auth_failed


class AssistantExtras(BaseModel):
    """The two facts the worker itself decides on: which tools to load and which runtime to use."""

    model_config = ConfigDict(extra="ignore")

    screen_ui_guidance: bool = False
    voice_help_intent: str | None = None


class GPTLiveInstructions(BaseModel):
    """Instructions for a speech-to-speech session: the voice model, its delegate, and how to open."""

    model_config = ConfigDict(frozen=True)

    voice: str = Field(min_length=1)
    backend: str = Field(min_length=1)
    opening: str = Field(min_length=1)


class AssistantSession(BaseModel):
    """What the worker needs to run one assistant session; every text arrives rendered.

    ``instructions`` is required. ``greeting`` is the backend's opening line;
    without one the model generates its own opening. ``help_corpus`` enables
    the FAQ search tool; ``gpt_live`` makes speech-to-speech possible.
    """

    model_config = ConfigDict(extra="ignore")

    session_id: str = Field(min_length=1)
    worker_type: WorkerType
    candidate_ref: str = ""
    instructions: str = Field(min_length=1)
    greeting: str | None = None
    help_corpus: HelpCorpus | None = None
    gpt_live: GPTLiveInstructions | None = None
    extras: AssistantExtras = Field(default_factory=AssistantExtras)

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
    result = sync_get_json(endpoints.required_base_url(), metadata.bootstrap_path, headers=endpoints.secret_headers(), log_prefix="assistant_bootstrap")
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
    result = sync_post_json(
        endpoints.required_base_url(), SCENE_PATH_TEMPLATE.format(session_id=session_id), scene,
        headers=endpoints.secret_headers(), log_prefix="assistant_scene",
    )
    instructions = (result.data or {}).get("instructions") if result.ok else None
    if not isinstance(instructions, str) or not instructions.strip():
        raise BootstrapError(f"scene instructions unavailable for session {session_id} (HTTP {result.status})")
    return instructions
