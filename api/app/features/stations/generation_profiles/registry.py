"""Load generation profiles (block hints from B2C models; system prompts from b2c_prompts)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.exam_settings import ExamSettings
from app.features.generation import service as generation

_GENERATED_DIR = Path(__file__).resolve().parent / "_generated"


@dataclass(frozen=True)
class GenerationProfileMeta:
    """A profile's identity, without its content: what the picker in the author UI lists."""

    profile_key: str
    label: str
    exam_code: str | None
    ortho_station_type: str | None


@dataclass(frozen=True)
class GenerationProfile:
    """A profile in full: its identity plus the per-block hints it feeds to autogeneration."""

    meta: GenerationProfileMeta
    block_hints: dict[str, str]

    def system_prompt(self) -> str:
        """This profile's system prompt for autogeneration, or empty for the custom profile."""
        if self.meta.profile_key == "custom":
            return ""
        # A profile's key is also its station prompt's key in `generation`.
        return generation.station_prompt_for_key(self.meta.profile_key)


def _json_path_for_key(profile_key: str) -> Path:
    return _GENERATED_DIR / f"{profile_key.replace('.', '_')}.json"


@lru_cache(maxsize=1)
def _load_all_profiles() -> dict[str, GenerationProfile]:
    """Every generation profile shipped in `_generated/`, read from disk once and cached."""
    profiles: dict[str, GenerationProfile] = {}
    for path in _GENERATED_DIR.glob("*.json"):
        if path.name == "index.json":
            continue
        raw = json.loads(path.read_text(encoding="utf-8"))
        key = str(raw.get("profileKey") or "")
        if not key:
            continue
        meta = GenerationProfileMeta(
            profile_key=key,
            label=str(raw.get("label") or key),
            exam_code=raw.get("examCode"),
            ortho_station_type=raw.get("orthoStationType"),
        )
        hints = raw.get("blockHints")
        block_hints = dict(hints) if isinstance(hints, dict) else {}
        profiles[key] = GenerationProfile(meta=meta, block_hints=block_hints)
    return profiles


def list_profile_meta() -> list[GenerationProfileMeta]:
    """Every profile's identity, for the picker. Read from the prebuilt index when there is one."""
    index_path = _GENERATED_DIR / "index.json"
    if index_path.is_file():
        index = json.loads(index_path.read_text(encoding="utf-8"))
        if isinstance(index, list):
            return [
                GenerationProfileMeta(
                    profile_key=str(entry["profileKey"]),
                    label=str(entry.get("label") or entry["profileKey"]),
                    exam_code=entry.get("examCode"),
                    ortho_station_type=entry.get("orthoStationType"),
                )
                for entry in index
                if isinstance(entry, dict) and entry.get("profileKey")
            ]
    return [profile.meta for profile in _load_all_profiles().values()]


def get_profile(profile_key: str) -> GenerationProfile | None:
    """One profile by key, or `None` when no shipped profile has it."""
    return _load_all_profiles().get(profile_key)


def default_profile_key_for_exam(
    exam_settings: ExamSettings,
    station_subtype: str | None = None,
) -> str:
    """The profile a station of this exam (and of this subtype, if it lists one) generates from by default."""
    subtype = exam_settings.subtype(station_subtype)
    if subtype is not None:
        return subtype.generation_profile
    return exam_settings.generation.default_profile


def resolve_profile_key_from_structure(
    structure: dict[str, Any],
    exam_settings: ExamSettings,
) -> str:
    """The profile a template names explicitly, or the exam's default when it names none."""
    generation = structure.get("generation")
    if isinstance(generation, dict):
        key = generation.get("profileKey")
        if isinstance(key, str) and key.strip():
            return key.strip()
    return default_profile_key_for_exam(exam_settings)
