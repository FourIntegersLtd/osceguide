"""Which backend a worker talks to, as data.

``BackendEndpoints`` describes one backend: where it is, how to authenticate,
and the shape of its cloud-slot routes. ``BackendRegistry`` holds several,
keyed by a label chosen by whoever configures the deployment. A dispatching
backend names its own label in the job metadata; the worker treats the label
as an opaque key.

Configuration is a JSON object in ``VOICE_BACKENDS_JSON``::

    {
      "practice": {
        "base_url_env": "FLASK_BACKEND_URL",
        "secret_env": "B2C_LIVEKIT_WORKER_SECRET",
        "secret_header": "X-B2C-Worker-Secret",
        "slot_release_path": "/api/worker/livekit-cloud-slot/release",
        "slot_extend_path": "/api/worker/livekit-cloud-slot/extend",
        "slot_payload_key": "room_name",
        "attempt_path": "/api/worker/attempts/{attempt_id}",
        "transcript_chunks_path": "/api/worker/attempts/{attempt_id}/transcript-chunks",
        "transcript_path": "/api/worker/attempts/{attempt_id}/transcript"
      }
    }

The three ``*_path`` keys for the assessment routes are optional and default
to the values shown; a backend that mounts its worker routes under a prefix
(say ``/api/org/worker/attempts/{attempt_id}``) declares its own. Each must
contain the ``{attempt_id}`` placeholder.

URLs and secrets are read from the named environment variables at call time,
so the JSON itself carries no secrets.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

BACKENDS_ENV = "VOICE_BACKENDS_JSON"

ATTEMPT_ID_PLACEHOLDER = "{attempt_id}"
DEFAULT_ATTEMPT_PATH = "/api/worker/attempts/{attempt_id}"
DEFAULT_TRANSCRIPT_CHUNKS_PATH = "/api/worker/attempts/{attempt_id}/transcript-chunks"
DEFAULT_TRANSCRIPT_PATH = "/api/worker/attempts/{attempt_id}/transcript"


class BackendRegistryError(RuntimeError):
    """Configuration is missing, malformed, or names an unknown backend."""


@dataclass(frozen=True)
class BackendEndpoints:
    label: str
    base_url_env: str
    secret_env: str
    secret_header: str
    slot_release_path: str
    slot_extend_path: str
    slot_payload_key: str
    attempt_path: str = DEFAULT_ATTEMPT_PATH
    transcript_chunks_path: str = DEFAULT_TRANSCRIPT_CHUNKS_PATH
    transcript_path: str = DEFAULT_TRANSCRIPT_PATH

    def __post_init__(self) -> None:
        for name in _PATH_TEMPLATE_KEYS:
            if ATTEMPT_ID_PLACEHOLDER not in getattr(self, name):
                raise BackendRegistryError(f"backend {self.label!r}: {name} must contain {ATTEMPT_ID_PLACEHOLDER}")

    def base_url(self) -> str | None:
        url = (os.getenv(self.base_url_env) or "").strip().rstrip("/")
        return url or None

    def required_base_url(self) -> str:
        url = self.base_url()
        if not url:
            raise BackendRegistryError(f"{self.base_url_env} must be set for backend {self.label!r}")
        return url

    def secret_headers(self) -> dict[str, str]:
        secret = (os.getenv(self.secret_env) or "").strip()
        return {self.secret_header: secret} if secret else {}

    def slot_endpoint(self, action: str) -> str | None:
        base = self.base_url()
        if not base:
            return None
        path = self.slot_release_path if action == "release" else self.slot_extend_path
        return f"{base}{path}"

    def slot_payload(self, room_name: str) -> dict[str, str]:
        return {self.slot_payload_key: room_name}

    def url(self, path: str) -> str:
        return f"{self.required_base_url()}{path}"

    # -- assessment worker routes, keyed by attempt --------------------------

    def attempt_url(self, attempt_id: str) -> str:
        return self.url(self.attempt_path.format(attempt_id=attempt_id))

    def transcript_chunks_url(self, attempt_id: str) -> str:
        return self.url(self.transcript_chunks_path.format(attempt_id=attempt_id))

    def transcript_url(self, attempt_id: str) -> str:
        return self.url(self.transcript_path.format(attempt_id=attempt_id))


_REQUIRED_KEYS = (
    "base_url_env",
    "secret_env",
    "secret_header",
    "slot_release_path",
    "slot_extend_path",
    "slot_payload_key",
)
_PATH_TEMPLATE_KEYS = ("attempt_path", "transcript_chunks_path", "transcript_path")


class BackendRegistry:
    def __init__(self, backends: dict[str, BackendEndpoints]) -> None:
        self._backends = dict(backends)

    @classmethod
    def from_json(cls, raw: str) -> "BackendRegistry":
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise BackendRegistryError(f"{BACKENDS_ENV} is not valid JSON: {exc}") from exc
        if not isinstance(data, dict) or not data:
            raise BackendRegistryError(f"{BACKENDS_ENV} must be a non-empty JSON object")
        backends: dict[str, BackendEndpoints] = {}
        for label, spec in data.items():
            if not isinstance(spec, dict):
                raise BackendRegistryError(f"backend {label!r} must be an object")
            missing = [key for key in _REQUIRED_KEYS if not str(spec.get(key, "")).strip()]
            if missing:
                raise BackendRegistryError(f"backend {label!r} is missing {missing}")
            fields = {key: str(spec[key]).strip() for key in _REQUIRED_KEYS}
            # Optional route templates: an absent or blank key keeps the default.
            fields.update({key: str(spec[key]).strip() for key in _PATH_TEMPLATE_KEYS if str(spec.get(key, "")).strip()})
            backends[label] = BackendEndpoints(label=label, **fields)
        return cls(backends)

    @classmethod
    def from_env(cls) -> "BackendRegistry":
        raw = (os.getenv(BACKENDS_ENV) or "").strip()
        if not raw:
            raise BackendRegistryError(f"{BACKENDS_ENV} must be set")
        return cls.from_json(raw)

    def labels(self) -> tuple[str, ...]:
        return tuple(self._backends)

    def get(self, label: str) -> BackendEndpoints:
        try:
            return self._backends[label]
        except KeyError:
            raise BackendRegistryError(f"unknown backend {label!r}; configured: {sorted(self._backends)}") from None
