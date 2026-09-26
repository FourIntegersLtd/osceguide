"""The generation-profile catalog, as the station routes expose it."""

from __future__ import annotations

from typing import Any

from app.features.stations.errors import GenerationProfileNotFound
from app.features.stations.generation_profiles.registry import get_profile, list_profile_meta
from app.features.stations.generation_profiles.resolve import effective_block_hints_for_profile


def list_profiles() -> list[dict[str, Any]]:
    """Every generation profile's identity, for the author's picker."""
    return [
        {
            "profileKey": meta.profile_key,
            "label": meta.label,
            "examCode": meta.exam_code,
            "orthoStationType": meta.ortho_station_type,
        }
        for meta in list_profile_meta()
    ]


def profile_detail(profile_key: str) -> dict[str, Any]:
    """One profile in full: its system prompt and block hints, or refuse if it does not exist."""
    profile = get_profile(profile_key)
    if profile is None:
        raise GenerationProfileNotFound()
    system_prompt = ""
    if profile_key != "custom":
        system_prompt = profile.system_prompt()
    return {
        "profileKey": profile.meta.profile_key,
        "label": profile.meta.label,
        "examCode": profile.meta.exam_code,
        "orthoStationType": profile.meta.ortho_station_type,
        "systemPrompt": system_prompt,
        "blockHints": effective_block_hints_for_profile(profile_key),
    }
