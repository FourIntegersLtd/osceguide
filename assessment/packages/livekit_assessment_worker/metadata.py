"""What a dispatching backend must put in the job metadata."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


class MetadataError(ValueError):
    """Job metadata is missing or malformed."""


@dataclass(frozen=True)
class DispatchMetadata:
    """The three values a job needs to start: which attempt, which backend, and which participant to listen to."""

    attempt_id: str
    backend: str
    candidate_ref: str


def _pick(data: dict[str, Any], *keys: str) -> str:
    """The first non-blank value found under any of these keys, as trimmed text, or an empty string."""
    for key in keys:
        value = data.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def parse_dispatch_metadata(raw: str | None) -> DispatchMetadata:
    """Accepts snake_case and camelCase keys; all three fields are required.

    ``candidate_ref`` is the LiveKit identity (or its prefix) of the one
    participant the AI listens to. Rooms may hold other humans, so a job
    without it cannot safely pick anyone.
    """
    try:
        payload = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        raise MetadataError(f"job metadata is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise MetadataError("job metadata must be a JSON object")
    fields = {
        "attempt_id": _pick(payload, "attempt_id", "attemptId"),
        "backend": _pick(payload, "backend"),
        "candidate_ref": _pick(payload, "candidate_ref", "candidateRef"),
    }
    missing = [name for name, value in fields.items() if not value]
    if missing:
        raise MetadataError(f"job metadata is missing {missing}")
    return DispatchMetadata(**fields)
