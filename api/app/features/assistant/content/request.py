"""Validate the ``client`` block a frontend sends with a voice session request."""

from __future__ import annotations

from typing import Any

from .models import MAX_NAV_FIELD_CHARS, MAX_NAV_ITEMS, MAX_ROUTE_CHARS, SURFACES


class ClientContextError(ValueError):
    """The client block is malformed; the message is safe to return to the caller."""


def _text(value: Any, *, field: str, limit: int) -> str:
    """This field as a trimmed, length-capped string, or raise if it is not a string."""
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ClientContextError(f"client.{field} must be a string")
    return value.strip()[:limit]


# The longest topic title kept. It is a question the person typed or the title
# of something they were reading, and it is read into the tutor's prompt.
MAX_TOPIC_CHARS = 200

# The kinds of reading a topic can come from, as `media` names them.
TOPIC_KINDS = ("summary", "slide_deck", "podcast", "blog")


def parse_topic(raw: Any) -> dict[str, str] | None:
    """The ``topic`` a conversation was opened on, or ``None`` when the request named none.

    A topic is `{title, kind?, slug?}`: what to talk about, and the reading it
    came from when it came from one. A blank title is no topic. The title is
    length-capped here and quoted by the prompt, so it is only ever a subject.
    """
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ClientContextError("topic must be an object")
    # Whitespace is collapsed before the cap, so a padded title is not cut short.
    raw_title = _text(raw.get("title"), field="topic.title", limit=MAX_TOPIC_CHARS * 4)
    title = " ".join(raw_title.split())[:MAX_TOPIC_CHARS]
    if not title:
        return None
    kind = _text(raw.get("kind"), field="topic.kind", limit=32).lower()
    if kind and kind not in TOPIC_KINDS:
        raise ClientContextError(f"topic.kind must be one of {', '.join(TOPIC_KINDS)}")
    return {
        "title": title.strip(),
        "kind": kind,
        "slug": _text(raw.get("slug"), field="topic.slug", limit=MAX_ROUTE_CHARS),
    }


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
    for entry in navigation_raw[:MAX_NAV_ITEMS]:
        if not isinstance(entry, dict):
            raise ClientContextError("client.navigation items must be objects")
        key = _text(entry.get("key"), field="navigation.key", limit=MAX_NAV_FIELD_CHARS)
        if not key:
            continue
        navigation.append(
            {
                "key": key,
                "label": _text(entry.get("label"), field="navigation.label", limit=MAX_NAV_FIELD_CHARS)
                or key,
                "path": _text(entry.get("path"), field="navigation.path", limit=MAX_ROUTE_CHARS),
            }
        )
    return {
        "surface": surface,
        "route": _text(raw.get("route"), field="route", limit=MAX_ROUTE_CHARS),
        "navigation": navigation,
    }
