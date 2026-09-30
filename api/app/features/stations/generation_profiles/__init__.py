"""Station autogenerate profiles (B2C-aligned)."""

from app.features.stations.generation_profiles.registry import (
    GenerationProfile,
    GenerationProfileMeta,
    default_profile_key_for_exam,
    get_profile,
    list_profile_meta,
)
from app.features.stations.generation_profiles.resolve import (
    effective_block_hints_for_profile,
    profile_key_for_structure,
    resolve_block_generation_hints,
    resolve_system_prompt,
)

__all__ = [
    "GenerationProfile",
    "GenerationProfileMeta",
    "default_profile_key_for_exam",
    "effective_block_hints_for_profile",
    "get_profile",
    "list_profile_meta",
    "profile_key_for_structure",
    "resolve_block_generation_hints",
    "resolve_system_prompt",
]
