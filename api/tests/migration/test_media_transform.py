"""Transforms for B2C study material → platform media rows."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.media.models import MediaItem
from app.migration.load_media import load_media
from app.migration.media import (
    blog_from_document,
    media_from_document,
    podcast_from_summary,
    slide_deck_from_document,
    summary_from_document,
)
from app.migration.sync_media_podcasts import sync_podcast_urls_from_documents
from tests.support.catalog import ensure_exam

pytestmark = pytest.mark.db

NOW = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)


def sca_summary(**overrides: object) -> dict:
    base = {
        "id": "doc-1",
        "app_type": "sca",
        "_media_kind": "summary",
        "summary_id": "sum-42",
        "name": "Asthma",
        "red_flags": ["Night symptoms"],
        "examinations": ["History"],
        "brief_management": ["SABA PRN"],
        "psychosocial_aspects": ["Impact on work"],
        "specialties": ["Respiratory Medicine"],
        "created_at": "2026-01-01T00:00:00Z",
        "podcast_url": "https://cdn.example.com/a.mp3",
    }
    base.update(overrides)
    return base


def test_summary_transform_preserves_clinical_fields_and_podcast() -> None:
    row = summary_from_document(sca_summary())
    assert row.kind == "summary"
    assert row.exam_code == "sca"
    assert row.legacy_ref == "sca:summary:sum-42"
    assert row.slug == "sca-summary-sum-42"
    assert row.content["podcast_url"] == "https://cdn.example.com/a.mp3"
    assert row.content["specialties"] == ["Respiratory Medicine"]
    assert row.content["red_flags"] == ["Night symptoms"]


def test_podcast_derived_only_when_url_present() -> None:
    summary = summary_from_document(sca_summary())
    podcast = podcast_from_summary(summary)
    assert podcast is not None
    assert podcast.kind == "podcast"
    assert podcast.legacy_ref == "sca:podcast:sum-42"
    assert podcast.content["audio_url"] == "https://cdn.example.com/a.mp3"
    assert podcast.content["summary_slug"] == summary.slug

    no_audio = summary_from_document(sca_summary(podcast_url=""))
    assert podcast_from_summary(no_audio) is None


def test_media_from_document_yields_summary_and_podcast() -> None:
    rows = media_from_document(sca_summary())
    assert len(rows) == 2
    assert {r.kind for r in rows} == {"summary", "podcast"}


def test_blog_transform_keeps_updated_at_in_content() -> None:
    doc = {
        "app_type": "sca",
        "_media_kind": "blog",
        "blog_id": "b-1",
        "title": "Tips",
        "content": "# Hello",
        "url": "top-tips",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-02-01T00:00:00Z",
    }
    row = blog_from_document(doc)
    assert row.slug == "sca-top-tips"
    assert row.content["updated_at"] == "2026-02-01T00:00:00Z"


def test_slide_deck_normalizes_dict_slides() -> None:
    doc = {
        "app_type": "plab",
        "_media_kind": "slide_deck",
        "slide_id": "sl-9",
        "topic": "Sepsis",
        "about": "In this video you will learn sepsis basics for the exam.",
        "slides": {"0": {"title": "Intro"}, "1": {"title": "Management"}},
        "final_video_url": "https://video.example/v.mp4",
        "specialty": "Emergency Medicine",
        "created_at": "2026-01-01T00:00:00Z",
    }
    row = slide_deck_from_document(doc)
    assert row.exam_code == "plab"
    assert isinstance(row.content["slides"], list)
    assert len(row.content["slides"]) == 2
    assert row.content["final_video_url"] == "https://video.example/v.mp4"


async def test_load_media_is_idempotent_on_legacy_ref(db_session: AsyncSession) -> None:
    await ensure_exam(db_session, "sca")
    rows = media_from_document(sca_summary())
    first = await load_media(db_session, rows, now=NOW)
    assert first.media_created == 2
    assert first.media_existing == 0

    second = await load_media(db_session, rows, now=NOW)
    assert second.media_created == 0
    assert second.media_existing == 2

    count = int(await db_session.scalar(select(func.count()).select_from(MediaItem)) or 0)
    assert count == 2


async def test_sync_podcast_urls_backfills_after_summary_without_url(
    db_session: AsyncSession,
) -> None:
    await ensure_exam(db_session, "sca")
    await load_media(
        db_session,
        [summary_from_document(sca_summary(podcast_url=""))],
        now=NOW,
    )
    report = await sync_podcast_urls_from_documents(
        db_session,
        [sca_summary(podcast_url="https://cdn.example.com/a.mp3")],
        now=NOW,
    )
    assert report.summaries_updated == 1
    assert report.podcasts_created == 1
    assert report.problems == []

    summary = await db_session.scalar(select(MediaItem).where(MediaItem.kind == "summary").limit(1))
    podcast = await db_session.scalar(select(MediaItem).where(MediaItem.kind == "podcast").limit(1))
    assert summary is not None
    assert podcast is not None
    assert summary.content.get("podcast_url") == "https://cdn.example.com/a.mp3"
    assert podcast.content.get("audio_url") == "https://cdn.example.com/a.mp3"
