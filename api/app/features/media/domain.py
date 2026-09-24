"""Study material that is not a station: slides, summaries, blogs, podcasts.

One kind field rather than a table each. b2c has four collections per product
for these — sixteen in total — with the same publish-and-read logic copied
across them.
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


class MediaKind(StrEnum):
    SLIDE_DECK = "slide_deck"
    SUMMARY = "summary"
    BLOG = "blog"
    PODCAST = "podcast"


class UnknownMediaKind(ValueError):
    pass


class NotEditable(Exception):
    pass


class AlreadyPublished(Exception):
    pass


class UnusableTitle(ValueError):
    pass


class EmptyQuery(ValueError):
    pass


class QueryTooLong(ValueError):
    pass


class InvalidListStatus(ValueError):
    pass


class NotDeletable(Exception):
    pass


def normalize_kind(kind: str) -> str:
    try:
        return str(MediaKind((kind or "").strip().lower()))
    except ValueError as exc:
        raise UnknownMediaKind(f"{kind!r} is not a kind of study material.") from exc


def is_public(*, status: str) -> bool:
    return status == "published"


def ensure_editable(*, status: str) -> None:
    if status != "draft":
        raise NotEditable("Published material is edited by replacing it, not in place.")


def ensure_deletable(*, status: str) -> None:
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
    left when an item has none. Truncated at a word boundary for the reason
    `slugify` is: half a word reads as a bug rather than as an abbreviation.
    """
    text = " ".join((summary or "").split()) or title.strip()
    if len(text) <= MAX_EXCERPT:
        return text
    head, _, _ = text[:MAX_EXCERPT].rpartition(" ")
    return f"{(head or text[:MAX_EXCERPT]).rstrip(' ,.;:')}…"


def specialty_of(content: dict[str, Any]) -> str | None:
    """The specialty an item is filed under, read out of the document.

    The authoring payload carries it twice — a `specialties` list, which is
    what the staff facets read, and the singular `specialty` string the
    retiring consumer client wrote beside it. The list wins, because that is
    the precedence both readers already used; a document with neither has no
    specialty, which is a normal thing for a blog post or an episode to lack.
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

    b2c stored a blog's `updated_at` on the document rather than in a column,
    so a migrated item's real edit date is in there and nowhere else — the row
    would say the day it was imported. A value that is not a date is ignored
    rather than refused: a document nobody validates is not a place to raise
    from while reading a list.
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
