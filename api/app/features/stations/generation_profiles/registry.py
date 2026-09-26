"""Load generation profiles (block hints from B2C models; system prompts from b2c_prompts)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.features.generation import service as generation

_GENERATED_DIR = Path(__file__).resolve().parent / "_generated"

EXAM_DEFAULT_PROFILE: dict[str, str] = {
    "sca": "sca.station",
    "plab": "plab.station",
    "casc": "casc.station",
    "ortho": "ortho.clinical",
}

ORTHO_PROFILE_BY_TYPE: dict[str, str] = {
    "clinical": "ortho.clinical",
    "communication": "ortho.communication",
    "prioritisation": "ortho.prioritisation",
    "portfolio": "ortho.portfolio",
}


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
        exam = self.meta.exam_code or "sca"
        ortho = self.meta.ortho_station_type
        return generation.station_system_prompt(exam, ortho)


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
    return _load_all_profiles().get(profile_key)


def default_profile_key_for_exam(
    exam_code: str | None,
    ortho_station_type: str | None = None,
) -> str:
    """The profile a station of this exam (and, for ortho, this station type) generates from by default."""
    exam = (exam_code or "sca").strip().lower()
    if exam == "ortho" and ortho_station_type:
        ortho = ortho_station_type.strip().lower()
        return ORTHO_PROFILE_BY_TYPE.get(ortho, "ortho.clinical")
    return EXAM_DEFAULT_PROFILE.get(exam, "sca.station")


def resolve_profile_key_from_structure(
    structure: dict[str, Any],
    exam_code: str | None,
) -> str:
    """The profile a template names explicitly, or the exam's default when it names none."""
    generation = structure.get("generation")
    if isinstance(generation, dict):
        key = generation.get("profileKey")
        if isinstance(key, str) and key.strip():
            return key.strip()
    return default_profile_key_for_exam(exam_code)
