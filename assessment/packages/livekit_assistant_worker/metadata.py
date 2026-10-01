"""What a dispatching backend must put in the job metadata."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


class MetadataError(ValueError):
    """Job metadata is missing or malformed."""


@dataclass(frozen=True)
class DispatchMetadata:
    """The job metadata a backend sends: the session, which backend sent it, and who the candidate is."""

    session_id: str
    backend: str
    candidate_ref: str = ""


def _pick(data: dict[str, Any], *keys: str) -> str:
    """The first non-blank value among the given keys, as text, or an empty string."""
    for key in keys:
        value = data.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def parse_dispatch_metadata(raw: str | None) -> DispatchMetadata:
    """Accepts snake_case and camelCase keys; session id and backend are required."""
    try:
        data = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        raise MetadataError(f"job metadata is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise MetadataError("job metadata must be a JSON object")
    session_id = _pick(data, "session_id", "sessionId")
    backend = _pick(data, "backend")
    missing = [name for name, value in (("session_id", session_id), ("backend", backend)) if not value]
    if missing:
        raise MetadataError(f"job metadata is missing {missing}")
    return DispatchMetadata(session_id=session_id, backend=backend, candidate_ref=_pick(data, "candidate_ref", "candidateRef"))
