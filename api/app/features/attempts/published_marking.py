"""Platform-default marking rubrics until org rubrics land in the database.

The engine no longer ships a catalogue or default marking prompts: a rubric is
framework data plus the prompt somebody wrote. For the four published exams we
still load the legacy catalogue from the b2c vendor checkout (same frameworks
the old engine shipped) and attach the matching system prompt.
"""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.logging import get_logger
from app.features.catalog.domain import PUBLISHED_EXAMS

log = get_logger(__name__)

_KNOWN_FRAMEWORK_IDS = frozenset(e.framework_id for e in PUBLISHED_EXAMS)


def canonical_framework_id(raw: str, *, exam_code: str | None = None) -> str:
    """Return a published framework id string, not an exam row uuid."""
    key = (raw or "").strip()
    if key in _KNOWN_FRAMEWORK_IDS:
        return key
    if exam_code:
        from app.features.catalog.domain import exam_by_code

        return exam_by_code(exam_code).framework_id
    return key


@lru_cache(maxsize=1)
def _legacy_vendor_root() -> Path | None:
    """`backend/b2c-api/vendor/osce-assessment` when this repo is checked out."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "b2c-api" / "vendor" / "osce-assessment"
        if (candidate / "osce_assessment" / "catalog.py").is_file():
            return candidate
    return None


def _import_legacy_catalog() -> Any:
    root = _legacy_vendor_root()
    if root is None:
        raise RuntimeError(
            "Published exam frameworks are not available: add "
            "backend/b2c-api/vendor/osce-assessment or install a rubric on the attempt."
        )
    vendor = str(root)
    # `make engine-dev` installs a newer `osce_assessment` without `catalog`.
    # Load the vendored copy in isolation so marking still uses the four exams.
    saved_path = sys.path[:]
    for name in list(sys.modules):
        if name == "osce_assessment" or name.startswith("osce_assessment."):
            del sys.modules[name]
    sys.path = [vendor] + [p for p in saved_path if p != vendor]
    try:
        from osce_assessment import catalog  # noqa: PLC0415
    finally:
        sys.path = saved_path
    return catalog


def marking_snapshot(framework_id: str) -> dict[str, Any]:
    """Rubric dict ready to freeze onto an attempt's evaluation_policy."""
    fid = canonical_framework_id(framework_id)
    legacy = _import_legacy_catalog()
    vendor = _legacy_vendor_root()
    assert vendor is not None
    saved_path = sys.path[:]
    for name in list(sys.modules):
        if name == "osce_assessment" or name.startswith("osce_assessment."):
            del sys.modules[name]
    sys.path = [str(vendor)] + [p for p in saved_path if p != str(vendor)]
    try:
        from osce_assessment.prompts import (  # noqa: PLC0415
            default_system_prompt_id,
            system_prompt,
        )

        framework = legacy.framework(fid)
        prompt = system_prompt(default_system_prompt_id(fid))
    finally:
        sys.path = saved_path
    payload = framework.model_dump(mode="json")
    payload["system_prompt"] = prompt
    return {
        "framework": payload,
        "system_prompt": prompt,
        "pacing": {},
        "marking_layout": None,
    }


def rubric_for_scoring(
    definition: dict[str, Any] | None,
    *,
    exam_code: str | None,
) -> dict[str, Any] | None:
    """Frozen rubric on the attempt, or the platform default for this exam."""
    from app.features.attempts.domain import rubric_for

    frozen = rubric_for(definition)
    if frozen is not None:
        return frozen
    raw = str((definition or {}).get("framework_id") or "")
    fid = canonical_framework_id(raw, exam_code=exam_code)
    if fid not in _KNOWN_FRAMEWORK_IDS:
        log.warning("no rubric and unknown framework id", framework_id=fid, exam_code=exam_code)
        return None
    try:
        return marking_snapshot(fid)
    except RuntimeError as exc:
        log.warning("platform marking snapshot unavailable", framework_id=fid, error=str(exc))
        return None
