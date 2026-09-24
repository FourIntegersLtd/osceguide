"""Validate the ``client`` block a frontend sends with a voice session request."""

from __future__ import annotations

from typing import Any

from .models import MAX_NAV_FIELD_CHARS, MAX_NAV_ITEMS, MAX_ROUTE_CHARS, SURFACES


class ClientContextError(ValueError):
    """The client block is malformed; the message is safe to return to the caller."""


def _text(value: Any, *, field: str, limit: int) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ClientContextError(f"client.{field} must be a string")
    return value.strip()[:limit]


def parse_client_context(raw: Any) -> dict[str, Any] | None:
    """The stored ``client`` dict, or ``None`` when the request carried none."""
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ClientContextError("client must be an object")
    surface = _text(raw.get("surface"), field="surface", limit=32).lower()
    if surface not in SURFACES:
        raise ClientContextError(f"client.surface must be one of {', '.join(SURFACES)}")
    navigation_raw = raw.get("navigation")
    if navigation_raw is None:
        navigation_raw = []
    if not isinstance(navigation_raw, list):
        raise ClientContextError("client.navigation must be a list")
    navigation = []
    for item in navigation_raw[:MAX_NAV_ITEMS]:
        if not isinstance(item, dict):
            raise ClientContextError("client.navigation items must be objects")
        key = _text(item.get("key"), field="navigation.key", limit=MAX_NAV_FIELD_CHARS)
        if not key:
            continue
        navigation.append(
            {
                "key": key,
                "label": _text(item.get("label"), field="navigation.label", limit=MAX_NAV_FIELD_CHARS) or key,
                "path": _text(item.get("path"), field="navigation.path", limit=MAX_ROUTE_CHARS),
            }
        )
    return {
        "surface": surface,
        "route": _text(raw.get("route"), field="route", limit=MAX_ROUTE_CHARS),
        "navigation": navigation,
    }
