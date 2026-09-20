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
    profile_key: str
    label: str
    exam_code: str | None
    ortho_station_type: str | None


@dataclass(frozen=True)
class GenerationProfile:
    meta: GenerationProfileMeta
    block_hints: dict[str, str]

    def system_prompt(self) -> str:
        if self.meta.profile_key == "custom":
            return ""
        exam = self.meta.exam_code or "sca"
        ortho = self.meta.ortho_station_type
        return generation.station_system_prompt(exam, ortho)


def _json_path_for_key(profile_key: str) -> Path:
    return _GENERATED_DIR / f"{profile_key.replace('.', '_')}.json"


@lru_cache(maxsize=1)
def _load_all_profiles() -> dict[str, GenerationProfile]:
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
    index_path = _GENERATED_DIR / "index.json"
    if index_path.is_file():
        index = json.loads(index_path.read_text(encoding="utf-8"))
        if isinstance(index, list):
            return [
                GenerationProfileMeta(
                    profile_key=str(row["profileKey"]),
                    label=str(row.get("label") or row["profileKey"]),
                    exam_code=row.get("examCode"),
                    ortho_station_type=row.get("orthoStationType"),
                )
                for row in index
                if isinstance(row, dict) and row.get("profileKey")
            ]
    return [p.meta for p in _load_all_profiles().values()]


def get_profile(profile_key: str) -> GenerationProfile | None:
    return _load_all_profiles().get(profile_key)


def default_profile_key_for_exam(
    exam_code: str | None,
    ortho_station_type: str | None = None,
) -> str:
    exam = (exam_code or "sca").strip().lower()
    if exam == "ortho" and ortho_station_type:
        ortho = ortho_station_type.strip().lower()
        return ORTHO_PROFILE_BY_TYPE.get(ortho, "ortho.clinical")
    return EXAM_DEFAULT_PROFILE.get(exam, "sca.station")


def resolve_profile_key_from_structure(
    structure: dict[str, Any],
    exam_code: str | None,
) -> str:
    generation = structure.get("generation")
    if isinstance(generation, dict):
        key = generation.get("profileKey")
        if isinstance(key, str) and key.strip():
            return key.strip()
    return default_profile_key_for_exam(exam_code)
