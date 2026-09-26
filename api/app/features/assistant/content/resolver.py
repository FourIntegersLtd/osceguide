"""Profile → pack: layer the overlays, then shape the content to the client's navigation."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from . import packs
from .models import (
    ADMIN_ROLE,
    SURFACE_ADMIN,
    SURFACE_EMPLOYER,
    SURFACE_EXAM,
    SURFACES,
    ClientProfile,
    ContentPack,
    FaqEntry,
    NavItem,
)
from .overlay import apply

DEFAULT_EXAM = "sca"
NAV_PLACEHOLDER = re.compile(r"\{nav\.([A-Za-z0-9_-]+)\}")


class UnsupportedSurfaceError(ValueError):
    """The profile names a surface this backend does not serve."""


def _str(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def resolve_client_profile(record: Mapping[str, Any]) -> ClientProfile:
    """The profile for a stored voice session record (``client``, ``exam_code``, ``role``).

    ``employer`` is refused: there is no separate employer product on this
    platform — the employer arm is B2B exam mode — so a session claiming that
    surface is a caller bug, not a pack that has not been written yet.
    """
    raw_client = record.get("client")
    client: Mapping[str, Any] = raw_client if isinstance(raw_client, dict) else {}
    role = _str(record.get("role")).lower()
    surface = _str(client.get("surface")).lower() or SURFACE_EXAM
    if surface == SURFACE_EMPLOYER:
        raise UnsupportedSurfaceError("employer sessions are not served by this backend")
    if surface not in SURFACES or (surface == SURFACE_ADMIN and role != ADMIN_ROLE):
        surface = SURFACE_EXAM
    navigation = tuple(
        NavItem(key=_str(entry.get("key")), label=_str(entry.get("label")), path=_str(entry.get("path")))
        for entry in (client.get("navigation") or [])
        if isinstance(entry, dict) and _str(entry.get("key"))
    )
    return ClientProfile(
        surface=surface,
        exam=(_str(record.get("exam_code")) or DEFAULT_EXAM).lower(),
        role=role,
        route=_str(client.get("route")),
        navigation=navigation,
    )


def _layered_pack(profile: ClientProfile) -> ContentPack:
    pack = packs.BASE
    exam_overlay = packs.EXAM_OVERLAYS.get(profile.exam)
    if exam_overlay is not None:
        pack = apply(pack, exam_overlay)
    surface_overlay = packs.SURFACE_OVERLAYS.get(profile.surface)
    if surface_overlay is not None:
        pack = apply(pack, surface_overlay)
    return pack


def _render(text: str, labels: Mapping[str, str]) -> str:
    return NAV_PLACEHOLDER.sub(lambda match: labels.get(match.group(1), match.group(1)), text)


def resolve_content_pack(profile: ClientProfile) -> ContentPack:
    """Layered pack with entries filtered to the client's navigation and placeholders rendered.

    Without a catalog (onboarding, legacy callers) nothing is filtered and the
    pack's default labels fill the placeholders.
    """
    pack = _layered_pack(profile)
    labels: dict[str, str] = {**pack.default_labels, **profile.nav_labels}
    visible_keys = set(profile.nav_labels)

    def visible(entry: FaqEntry) -> bool:
        return not visible_keys or set(entry.requires_nav) <= visible_keys

    faq = tuple(
        replace(entry, question=_render(entry.question, labels), answer=_render(entry.answer, labels))
        for entry in pack.faq
        if visible(entry)
    )
    return replace(
        pack,
        faq=faq,
        no_match_message=_render(pack.no_match_message, labels),
        greetings={kind: _render(text, labels) for kind, text in pack.greetings.items()},
    )
