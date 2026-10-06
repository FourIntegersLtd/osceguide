"""The rules for study material that is not a station: slides, summaries, blogs, podcasts.

Framework-free so a test or another slice can check a rule without a database. One kind
field carries what would otherwise be a separate table per product.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

MAX_SLUG = 80
MAX_QUERY = 300
MAX_EXCERPT = 160

_NON_SLUG = re.compile(r"[^a-z0-9]+")


# The four products a media item can be. Reaches openapi.json wherever it appears in a schema.
class MediaKind(StrEnum):
    SLIDE_DECK = "slide_deck"
    SUMMARY = "summary"
    BLOG = "blog"
    PODCAST = "podcast"


class UnknownMediaKind(ValueError):
    """Raised when a string does not name one of the four media kinds."""


class NotEditable(Exception):
    """Raised when someone tries to change a published item's content in place, rather than replacing it."""


class AlreadyPublished(Exception):
    """Raised when someone tries to publish an item that is already published."""


class UnusableTitle(ValueError):
    """Raised when a title has no characters a URL slug can be built from."""


class EmptyQuery(ValueError):
    """Raised when a search request carries no search text."""


class QueryTooLong(ValueError):
    """Raised when a search request's text is longer than `MAX_QUERY` characters."""


class InvalidListStatus(ValueError):
    """Raised when a list request's status filter is not draft, published, or all."""


class NotDeletable(Exception):
    """Raised when someone tries to delete an item that has already been published."""


def normalize_kind(kind: str) -> str:
    """The canonical spelling of a media kind, case- and whitespace-insensitive."""
    try:
        return str(MediaKind((kind or "").strip().lower()))
    except ValueError as exc:
        raise UnknownMediaKind(f"{kind!r} is not a kind of study material.") from exc


def is_public(*, status: str) -> bool:
    """Whether an item in this status is visible to a candidate browsing the library."""
    return status == "published"


def is_editable(*, status: str) -> bool:
    """Whether an item in this status may be changed in place: only a draft may."""
    return status == "draft"


def ensure_editable(*, status: str) -> None:
    """Refuses to change a published item's content in place; it must be replaced instead."""
    if not is_editable(status=status):
        raise NotEditable("A published item's content is replaced, not edited in place.")


def ensure_deletable(*, status: str) -> None:
    """Refuses to let a published item be deleted."""
    if status != "draft":
        raise NotDeletable("Only drafts can be deleted.")


def parse_authoring_status(raw: str | None) -> tuple[str, ...] | None:
    """`None` means published-only (consumer catalogue)."""
    if raw is None:
        return None
    key = raw.strip().lower()
    if key == "all":
        return ("draft", "published")
    if key in ("draft", "published"):
        return (key,)
    raise InvalidListStatus(f"{raw!r} is not a valid status filter (draft, published, all).")


def publish(*, status: str) -> str:
    """The `published` status, refusing to publish an item that already carries it."""
    if status == "published":
        raise AlreadyPublished("That is already published.")
    return "published"


def slugify(title: str) -> str:
    """A readable URL for a title.

    Truncated at a word boundary rather than mid-word, so a shortened slug still
    reads as words.
    """
    cleaned = _NON_SLUG.sub("-", (title or "").strip().lower()).strip("-")
    if not cleaned:
        raise UnusableTitle("That title has nothing a URL can be made from.")
    if len(cleaned) <= MAX_SLUG:
        return cleaned
    trimmed = cleaned[:MAX_SLUG]
    head, _, _ = trimmed.rpartition("-")
    return (head or trimmed).strip("-")


def clean_query(raw: str) -> str:
    """The search text trimmed, refusing one that is empty or longer than `MAX_QUERY` characters."""
    query = (raw or "").strip()
    if not query:
        # Searching for nothing would match everything, expensively.
        raise EmptyQuery("Type something to search for.")
    if len(query) > MAX_QUERY:
        raise QueryTooLong(f"A search is at most {MAX_QUERY} characters.")
    return query


def excerpt(summary: str | None, title: str) -> str:
    """A line of context under a search hit's title.

    The index answers with ids and scores, so there is no matched passage to
    quote — the summary is the closest thing to one, and the title is what is
    left when an item has none. Truncated at a word boundary, like `slugify`.
    """
    text = " ".join((summary or "").split()) or title.strip()
    if len(text) <= MAX_EXCERPT:
        return text
    head, _, _ = text[:MAX_EXCERPT].rpartition(" ")
    return f"{(head or text[:MAX_EXCERPT]).rstrip(' ,.;:')}…"


def specialty_of(content: dict[str, Any]) -> str | None:
    """The specialty an item is filed under, read out of the document.

    The payload may carry it as a `specialties` list or a singular
    `specialty` string; the list wins when both are present. A document with
    neither simply has no specialty.
    """
    many = content.get("specialties")
    if isinstance(many, list):
        for entry in many:
            if isinstance(entry, str) and entry.strip():
                return entry.strip()
    one = content.get("specialty")
    return one.strip() if isinstance(one, str) and one.strip() else None


def content_updated_at(content: dict[str, Any]) -> datetime | None:
    """The edit date the authoring payload carries, if it carries one.

    Stored in the document rather than in a column. A value that is not a
    date is ignored rather than refused: a document nobody validates is not a
    place to raise from while reading a list.
    """
    raw = content.get("updated_at")
    if not isinstance(raw, str):
        return None
    try:
        parsed = datetime.fromisoformat(raw.strip())
    except ValueError:
        return None
    # Every timestamp this API serves is offset-aware; a naive one from a
    # document that never said would serialize without its zone, and a list
    # sorted by a mixture of the two is not sorted.
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
