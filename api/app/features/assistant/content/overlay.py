"""Layering: a base pack plus per-exam and per-surface overlays."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace

from .models import ContentPack, FaqEntry, OnboardingScene, Persona


@dataclass(frozen=True)
class Overlay:
    add: tuple[FaqEntry, ...] = ()
    replace: tuple[FaqEntry, ...] = ()
    """Entries whose ``id`` already exists in the base; swapped in place."""
    remove: tuple[str, ...] = ()
    persona: Persona | None = None
    greetings: Mapping[str, str] | None = None
    """Merged over the base greetings, type by type."""
    onboarding_scenes: tuple[OnboardingScene, ...] | None = None
    """Replaces the base scenes wholesale when set."""
    default_labels: Mapping[str, str] | None = None


class OverlayError(ValueError):
    """An overlay names an entry the base does not have, or duplicates one."""


def apply(base: ContentPack, overlay: Overlay) -> ContentPack:
    base_ids = set(base.entry_ids())
    replacements = {entry.id: entry for entry in overlay.replace}
    unknown = sorted((set(replacements) | set(overlay.remove)) - base_ids)
    if unknown:
        raise OverlayError(f"overlay targets unknown FAQ entries: {unknown}")
    duplicates = sorted({entry.id for entry in overlay.add} & base_ids)
    if duplicates:
        raise OverlayError(f"overlay adds FAQ entries the base already has: {duplicates}")

    removed = set(overlay.remove)
    faq = (
        tuple(replacements.get(entry.id, entry) for entry in base.faq if entry.id not in removed)
        + overlay.add
    )
    greetings = {**base.greetings, **(overlay.greetings or {})}
    default_labels = {**base.default_labels, **(overlay.default_labels or {})}
    return replace(
        base,
        faq=faq,
        greetings=greetings,
        default_labels=default_labels,
        persona=overlay.persona or base.persona,
        onboarding_scenes=overlay.onboarding_scenes
        if overlay.onboarding_scenes is not None
        else base.onboarding_scenes,
    )
