"""A legacy item ticked as checked must read as current, so a later save starts no script rewrite."""

from __future__ import annotations

import sys
from pathlib import Path

from app.features.media.models import MediaItem
from app.features.media_production import script_check

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from mark_legacy_media_checked import CHECKED_BY, fill_missing_checks  # noqa: E402


def _summary() -> MediaItem:
    return MediaItem(
        kind="summary",
        title="Menieres",
        content={
            "red_flags": ["Sudden hearing loss"],
            "script": {"lines": [{"speaker": "A", "text": "Hello there."}]},
            "podcast_url": "https://example.test/a.mp3",
        },
    )


def test_a_summary_is_ticked_and_reads_as_current() -> None:
    row = _summary()

    added = fill_missing_checks(row)

    assert added["facts"] is True
    assert row.content["review"]["facts"]["checked_by"] == CHECKED_BY
    assert row.content["review"]["facts"]["claims"] == []
    if added["script"]:
        assert not script_check.script_out_of_date("summary", row.title, row.content)


def test_an_existing_check_is_never_replaced() -> None:
    row = _summary()
    row.content = {**row.content, "review": {"facts": {"claims": [], "checked_by": "someone"}}}

    fill_missing_checks(row)

    assert row.content["review"]["facts"]["checked_by"] == "someone"
