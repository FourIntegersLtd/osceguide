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
        "slot_payload_key": "room_name"
      }
    }

URLs and secrets are read from the named environment variables at call time,
so the JSON itself carries no secrets.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

BACKENDS_ENV = "VOICE_BACKENDS_JSON"


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


_REQUIRED_KEYS = (
    "base_url_env",
    "secret_env",
    "secret_header",
    "slot_release_path",
    "slot_extend_path",
    "slot_payload_key",
)


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
            backends[label] = BackendEndpoints(label=label, **{key: str(spec[key]).strip() for key in _REQUIRED_KEYS})
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
