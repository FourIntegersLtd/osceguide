"""Read-only catalog of station autogenerate profiles (B2C-aligned)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.core.auth import CurrentPrincipal
from app.core.errors import error_responses, Unauthenticated
from app.features.stations.generation_profiles.registry import get_profile, list_profile_meta
from app.features.stations.generation_profiles.resolve import effective_block_hints_for_profile

router = APIRouter(tags=["station-generation-profiles"])


@router.get(
    "/station-generation-profiles",
    responses=error_responses(Unauthenticated),
)
async def list_station_generation_profiles(_principal: CurrentPrincipal) -> dict[str, Any]:
    items = [
        {
            "profileKey": m.profile_key,
            "label": m.label,
            "examCode": m.exam_code,
            "orthoStationType": m.ortho_station_type,
        }
        for m in list_profile_meta()
    ]
    return {"items": items}


@router.get(
    "/station-generation-profiles/{profile_key}",
    responses=error_responses(Unauthenticated),
)
async def get_station_generation_profile(
    profile_key: str, _principal: CurrentPrincipal
) -> dict[str, Any]:
    profile = get_profile(profile_key)
    if profile is None:
        raise HTTPException(status_code=404, detail="profile_not_found")
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
