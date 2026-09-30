"""Transforms for B2C community → platform posts."""

from __future__ import annotations

from app.migration.b2c_community import (
    comment_from_document,
    question_from_document,
    reply_from_document,
)
from app.migration.legacy_ids import legacy_row_id


def test_question_legacy_ref_and_likes() -> None:
    row = question_from_document(
        {
            "_social_kind": "question",
            "app_type": "sca",
            "question_id": "q-1",
            "user_id": "u-1",
            "content": "How do I prepare?",
            "created_at": "2026-01-01T00:00:00Z",
            "liked_by": ["u-2"],
        }
    )
    assert row.legacy_ref == "sca:community:question:q-1"
    assert row.row_id == legacy_row_id(row.legacy_ref)
    assert row.kind == "question"
    assert len(row.likes) == 1
    assert row.likes[0].legacy_user_id == "u-2"


def test_reply_links_parent() -> None:
    row = reply_from_document(
        {
            "_social_kind": "reply",
            "app_type": "plab",
            "reply_id": "r-1",
            "question_id": "q-9",
            "user_id": "u-3",
            "content": "Practice stations daily.",
            "created_at": "2026-01-02T00:00:00Z",
        }
    )
    assert row.parent_legacy_ref == "plab:community:question:q-9"
    assert row.parent_row_id == legacy_row_id("plab:community:question:q-9")


def test_comment_carries_station() -> None:
    row = comment_from_document(
        {
            "_social_kind": "comment",
            "app_type": "sca",
            "comment_id": "c-1",
            "station_id": "st-42",
            "user_id": "u-1",
            "comment": "Great case.",
            "created_at": "2026-01-03T00:00:00Z",
        }
    )
    assert row.kind == "comment"
    assert row.legacy_station_id == "st-42"
