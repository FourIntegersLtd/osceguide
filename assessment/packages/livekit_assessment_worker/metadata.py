"""What a dispatching backend must put in the job metadata."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

BOOTSTRAP_PATH_TEMPLATE = "/api/worker/attempts/{attempt_id}"


class MetadataError(ValueError):
    """Job metadata is missing or malformed."""


@dataclass(frozen=True)
class DispatchMetadata:
    attempt_id: str
    backend: str
    candidate_ref: str = ""

    @property
    def bootstrap_path(self) -> str:
        return BOOTSTRAP_PATH_TEMPLATE.format(attempt_id=self.attempt_id)


def _pick(data: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = data.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def parse_dispatch_metadata(raw: str | None) -> DispatchMetadata:
    """Accepts snake_case and camelCase keys; attempt id and backend are required."""
    try:
        data = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        raise MetadataError(f"job metadata is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise MetadataError("job metadata must be a JSON object")
    attempt_id = _pick(data, "attempt_id", "attemptId")
    backend = _pick(data, "backend")
    missing = [name for name, value in (("attempt_id", attempt_id), ("backend", backend)) if not value]
    if missing:
        raise MetadataError(f"job metadata is missing {missing}")
    return DispatchMetadata(
        attempt_id=attempt_id,
        backend=backend,
        candidate_ref=_pick(data, "candidate_ref", "candidateRef"),
    )
