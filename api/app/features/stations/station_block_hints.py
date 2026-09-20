"""Per-block AI generation hints for station autogenerate."""

from __future__ import annotations

from typing import Any

from app.features.stations.generation_profiles.resolve import (
    profile_key_for_structure,
    resolve_block_generation_hints,
)


def hints_for_structure(structure: Any, *, exam_code: str | None = None) -> dict[str, str]:
    """Return generation hints for block ids present in the template structure."""
    if not isinstance(structure, dict):
        return {}
    profile_key = profile_key_for_structure(structure, exam_code)
    return resolve_block_generation_hints(structure, profile_key=profile_key)
