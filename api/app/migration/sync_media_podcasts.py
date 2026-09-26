"""Backfill `podcast_url` on imported summaries and podcast rows from Firestore.

The first `load_media` run only inserts by `legacy_ref`; it does not update rows
that were imported before a summary gained a `podcast_url` in Firestore. This
module reads summary documents (e.g. `summaries`, `plab_summaries`, …) and:

- sets `content.podcast_url` on the matching summary `media_items` row
- creates or updates the derived `kind=podcast` row (`content.audio_url`)
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog.models import Exam
from app.features.media.models import MediaItem
from app.migration.media import (
    MediaTransformError,
    podcast_from_summary,
    summary_from_document,
)


@dataclass
class PodcastSyncReport:
    """Counts from one podcast-URL backfill run, plus the summaries or podcasts it could not update."""

    firestore_with_url: int = 0
    firestore_no_url: int = 0
    summaries_updated: int = 0
    summaries_unchanged: int = 0
    summaries_missing: int = 0
    podcasts_created: int = 0
    podcasts_updated: int = 0
    podcasts_unchanged: int = 0
    problems: list[str] = field(default_factory=list)

    def problem(self, message: str) -> None:
        """Record one summary or podcast that could not be updated, and why."""
        self.problems.append(message)

    @property
    def has_no_problems(self) -> bool:
        """Whether this run recorded zero problems."""
        return not self.problems

    def summary(self) -> str:
        """One human-readable line covering every counter in this report."""
        return (
            f"firestore {self.firestore_with_url} with podcast_url / "
            f"{self.firestore_no_url} without; "
            f"summaries {self.summaries_updated} updated / "
            f"{self.summaries_unchanged} unchanged / "
            f"{self.summaries_missing} missing in db; "
            f"podcasts {self.podcasts_created} created / "
            f"{self.podcasts_updated} updated / "
            f"{self.podcasts_unchanged} unchanged; "
            f"problems {len(self.problems)}"
        )


def podcast_url_from_document(document: dict[str, Any]) -> str | None:
    """Read `podcast_url` or legacy `audio_url` from a Firestore summary export."""
    for key in ("podcast_url", "audio_url"):
        raw = document.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return None


async def _media_by_legacy_ref(session: AsyncSession) -> dict[str, MediaItem]:
    """Every already-imported media row that carries a `legacy_ref`, keyed by that reference."""
    media_rows = await session.execute(
        select(MediaItem).where(MediaItem.content["legacy_ref"].astext.isnot(None))
    )
    media_by_legacy_ref: dict[str, MediaItem] = {}
    for media_item in media_rows.scalars():
        legacy = media_item.content.get("legacy_ref")
        if isinstance(legacy, str) and legacy:
            media_by_legacy_ref[legacy] = media_item
    return media_by_legacy_ref


def _content_changed(before: dict[str, Any], after: dict[str, Any]) -> bool:
    """Whether applying a podcast URL actually changed a media row's `content`."""
    return before != after


async def sync_podcast_urls_from_documents(
    session: AsyncSession,
    documents: Sequence[dict[str, Any]],
    *,
    now: datetime | None = None,
) -> PodcastSyncReport:
    """Apply Firestore summary podcast URLs to existing `media_items` rows."""
    report = PodcastSyncReport()
    at = now or datetime.now(UTC)

    exam_rows = await session.execute(select(Exam.code, Exam.id))
    exams = {str(code).lower(): exam_id for code, exam_id in exam_rows.all()}
    by_legacy = await _media_by_legacy_ref(session)

    for raw in documents:
        if raw.get("_media_kind") not in (None, "summary"):
            continue

        url = podcast_url_from_document(raw)
        if not url:
            report.firestore_no_url += 1
            continue
        report.firestore_with_url += 1

        doc_id = raw.get("summary_id") or raw.get("id") or "?"
        try:
            summary_migrated = summary_from_document(raw)
            podcast_migrated = podcast_from_summary(summary_migrated)
        except MediaTransformError as exc:
            report.problem(f"summary {doc_id}: {exc}")
            continue

        if podcast_migrated is None:
            report.problem(f"summary {doc_id}: could not build podcast row")
            continue

        summary_row = by_legacy.get(summary_migrated.legacy_ref)
        if summary_row is None:
            report.summaries_missing += 1
            report.problem(
                f"summary {doc_id}: no media_items row for {summary_migrated.legacy_ref!r}; "
                "run import_b2c_media first"
            )
            continue

        summary_content = dict(summary_row.content)
        summary_content["podcast_url"] = url
        if _content_changed(summary_row.content, summary_content):
            summary_row.content = summary_content
            report.summaries_updated += 1
        else:
            report.summaries_unchanged += 1

        podcast_row = by_legacy.get(podcast_migrated.legacy_ref)
        if podcast_row is None:
            exam_id = exams.get(podcast_migrated.exam_code)
            if exam_id is None:
                report.problem(f"podcast {doc_id}: exam {podcast_migrated.exam_code!r} not in database")
                continue
            podcast_row = MediaItem(
                kind="podcast",
                slug=podcast_migrated.slug,
                title=podcast_migrated.title,
                summary=podcast_migrated.summary,
                content=podcast_migrated.content,
                exam_id=exam_id,
                author_id=None,
                status="published",
                published_at=podcast_migrated.published_at or at,
            )
            session.add(podcast_row)
            await session.flush()
            by_legacy[podcast_migrated.legacy_ref] = podcast_row
            report.podcasts_created += 1
            continue

        podcast_content = dict(podcast_row.content)
        podcast_content["audio_url"] = url
        podcast_content.setdefault("summary_id", podcast_migrated.content.get("summary_id"))
        podcast_content.setdefault("summary_slug", podcast_migrated.content.get("summary_slug"))
        if _content_changed(podcast_row.content, podcast_content):
            podcast_row.content = podcast_content
            report.podcasts_updated += 1
        else:
            report.podcasts_unchanged += 1

    return report


def inspect_summary_podcast_fields(documents: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Count how many exported summaries carry a podcast URL (for dry inspection)."""
    with_url = 0
    without = 0
    samples: list[dict[str, str]] = []
    for raw in documents:
        if raw.get("_media_kind") not in (None, "summary"):
            continue
        url = podcast_url_from_document(raw)
        sid = str(raw.get("summary_id") or raw.get("id") or "")
        exam = str(raw.get("app_type") or "?")
        if url:
            with_url += 1
            if len(samples) < 8:
                samples.append({"exam": exam, "summary_id": sid, "podcast_url": url[:120]})
        else:
            without += 1
    return {"summaries_with_podcast_url": with_url, "summaries_without": without, "samples": samples}
