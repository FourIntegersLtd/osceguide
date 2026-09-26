"""Turn legacy study-material documents into platform `media_items` rows."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.features.generation.normalizers import (
    normalize_blog_response,
    normalize_slide_deck_response,
    normalize_summary_response,
)
from app.features.media.domain import MAX_SLUG
from app.migration.users import UnknownLegacyProduct, exam_for_product, parse_timestamp

__all__ = [
    "MigratedMedia",
    "MediaTransformError",
    "UnknownLegacyProduct",
    "blog_from_document",
    "media_from_document",
    "podcast_from_summary",
    "slide_deck_from_document",
    "summary_from_document",
]

_NON_SLUG = re.compile(r"[^a-z0-9]+")

_NOT_CONTENT = frozenset(
    {
        "id",
        "app_type",
        "_media_kind",
        "created_at",
        "updated_at",
        "createdAt",
        "updatedAt",
    }
)


class MediaTransformError(Exception):
    """A document that cannot become a media row. Reported, never guessed at."""


@dataclass
class MigratedMedia:
    """One `media_items` row, ready for `load_media`."""

    legacy_ref: str
    kind: str
    exam_code: str
    slug: str
    title: str
    summary: str | None
    content: dict[str, Any]
    published_at: datetime | None = None
    warnings: list[str] = field(default_factory=list)


def _slug_part(raw: str) -> str:
    cleaned = _NON_SLUG.sub("-", (raw or "").strip().lower()).strip("-")
    return cleaned or "item"


def _bounded_slug(*parts: str) -> str:
    """Exam-prefixed slug within `MAX_SLUG`."""
    joined = "-".join(_slug_part(part) for part in parts if part)
    if not joined:
        raise MediaTransformError("cannot build slug from empty parts")
    if len(joined) <= MAX_SLUG:
        return joined
    trimmed = joined[:MAX_SLUG]
    head, _, _ = trimmed.rpartition("-")
    return (head or trimmed).strip("-") or trimmed[:MAX_SLUG]


def _product(document: dict[str, Any], *, product: str | None) -> str:
    raw = product or document.get("app_type")
    if not raw:
        raise MediaTransformError("document names no product")
    return exam_for_product(str(raw))


def _legacy_content(document: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in document.items() if key not in _NOT_CONTENT}


def _normalize_slides_array(slide_data: dict[str, Any]) -> None:
    slides_field = slide_data.get("slides")
    if not isinstance(slides_field, dict):
        return
    keys = list(slides_field.keys())
    if not keys or not all(str(key).isdigit() for key in keys):
        return
    sorted_keys = sorted(keys, key=lambda key: int(str(key)))
    slide_data["slides"] = [slides_field[key] for key in sorted_keys]


def summary_from_document(document: dict[str, Any], *, product: str | None = None) -> MigratedMedia:
    legacy_id = str(document.get("summary_id") or document.get("id") or "").strip()
    if not legacy_id:
        raise MediaTransformError("summary document has no summary_id")

    exam_code = _product(document, product=product)
    legacy_ref = f"{exam_code}:summary:{legacy_id}"
    slug = _bounded_slug(exam_code, "summary", legacy_id)

    base = _legacy_content(document)
    normalized = normalize_summary_response({**base, "name": base.get("name") or base.get("title")})
    content = {**base, **normalized}
    content["summary_id"] = legacy_id
    content["legacy_ref"] = legacy_ref

    title = str(normalized.get("title") or content.get("name") or f"Summary {legacy_id}")
    summary_line = normalized.get("summary")
    if summary_line is not None:
        summary_line = str(summary_line)

    published_at = parse_timestamp(document.get("created_at"))

    return MigratedMedia(
        legacy_ref=legacy_ref,
        kind="summary",
        exam_code=exam_code,
        slug=slug,
        title=title.strip(),
        summary=summary_line,
        content=content,
        published_at=published_at,
    )


def podcast_from_summary(summary: MigratedMedia) -> MigratedMedia | None:
    url = summary.content.get("podcast_url") or summary.content.get("audio_url")
    if not isinstance(url, str) or not url.strip():
        return None

    legacy_id = str(summary.content.get("summary_id") or "").strip()
    if not legacy_id:
        return None

    exam_code = summary.exam_code
    legacy_ref = f"{exam_code}:podcast:{legacy_id}"
    slug = _bounded_slug(exam_code, "podcast", legacy_id)

    content: dict[str, Any] = {
        "legacy_ref": legacy_ref,
        "summary_id": legacy_id,
        "summary_slug": summary.slug,
        "audio_url": url.strip(),
    }

    return MigratedMedia(
        legacy_ref=legacy_ref,
        kind="podcast",
        exam_code=exam_code,
        slug=slug,
        title=summary.title,
        summary=summary.summary,
        content=content,
        published_at=summary.published_at,
    )


def blog_from_document(document: dict[str, Any], *, product: str | None = None) -> MigratedMedia:
    legacy_id = str(document.get("blog_id") or document.get("id") or "").strip()
    if not legacy_id:
        raise MediaTransformError("blog document has no blog_id")

    exam_code = _product(document, product=product)
    legacy_ref = f"{exam_code}:blog:{legacy_id}"
    url_slug = str(document.get("url") or "").strip()
    slug = _bounded_slug(exam_code, url_slug) if url_slug else _bounded_slug(exam_code, "blog", legacy_id)

    base = _legacy_content(document)
    normalized = normalize_blog_response(
        {
            **base,
            "title": base.get("title"),
            "content": base.get("content"),
            "url": base.get("url"),
        }
    )
    content = {**base, **normalized}
    content["blog_id"] = legacy_id
    content["legacy_ref"] = legacy_ref
    if document.get("updated_at") is not None:
        content["updated_at"] = document.get("updated_at")

    title = str(normalized.get("title") or content.get("title") or f"Article {legacy_id}")
    summary_line = normalized.get("summary")
    if summary_line is not None:
        summary_line = str(summary_line)

    published_at = parse_timestamp(document.get("created_at"))

    return MigratedMedia(
        legacy_ref=legacy_ref,
        kind="blog",
        exam_code=exam_code,
        slug=slug,
        title=title.strip(),
        summary=summary_line,
        content=content,
        published_at=published_at,
    )


def slide_deck_from_document(document: dict[str, Any], *, product: str | None = None) -> MigratedMedia:
    legacy_id = str(document.get("slide_id") or document.get("id") or "").strip()
    if not legacy_id:
        raise MediaTransformError("slide document has no slide_id")

    exam_code = _product(document, product=product)
    legacy_ref = f"{exam_code}:slide_deck:{legacy_id}"
    slug = _bounded_slug(exam_code, "slide", legacy_id)

    base = _legacy_content(document)
    _normalize_slides_array(base)
    topic = str(base.get("topic") or base.get("title") or f"Slide deck {legacy_id}")
    normalized = normalize_slide_deck_response({**base, "title": topic})
    content = {**base, **normalized}
    content["slide_id"] = legacy_id
    content["legacy_ref"] = legacy_ref

    about = content.get("about")
    summary_line = str(about).strip() if isinstance(about, str) and about.strip() else None

    published_at = parse_timestamp(document.get("created_at"))

    return MigratedMedia(
        legacy_ref=legacy_ref,
        kind="slide_deck",
        exam_code=exam_code,
        slug=slug,
        title=topic.strip(),
        summary=summary_line,
        content=content,
        published_at=published_at,
    )


def media_from_document(document: dict[str, Any], *, product: str | None = None) -> list[MigratedMedia]:
    """Transform one export document; may yield a derived podcast row after a summary."""
    kind = document.get("_media_kind") or document.get("kind")
    if kind == "summary":
        summary = summary_from_document(document, product=product)
        media_items = [summary]
        podcast = podcast_from_summary(summary)
        if podcast is not None:
            media_items.append(podcast)
        return media_items
    if kind == "blog":
        return [blog_from_document(document, product=product)]
    if kind == "slide_deck":
        return [slide_deck_from_document(document, product=product)]

    raise MediaTransformError(f"unknown _media_kind {kind!r}")
