"""Study material that is not a station: slides, summaries, blogs, podcasts.

One kind field rather than a table each. b2c has four collections per product
for these — sixteen in total — with the same publish-and-read logic copied
across them.
"""

from __future__ import annotations

import re
from enum import StrEnum

MAX_SLUG = 80
MAX_QUERY = 300

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
