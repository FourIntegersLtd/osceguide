"""Transforms for B2C marketplace → platform tables."""

from __future__ import annotations

from app.migration.b2c_marketplace import post_from_document, session_from_document


def test_post_maps_claimed_status() -> None:
    row = post_from_document(
        {
            "_social_kind": "post",
            "app_type": "sca",
            "post_id": "p-1",
            "user_id": "u-owner",
            "scheduled_at": "2026-02-01T18:00:00Z",
            "status": "claimed",
            "claimed_by_user_id": "u-claimer",
            "claimed_at": "2026-01-31T12:00:00Z",
            "created_at": "2026-01-30T12:00:00Z",
        }
    )
    assert row.legacy_ref == "sca:marketplace:post:p-1"
    assert row.status == "claimed"
    assert row.claimed_by_legacy_user_id == "u-claimer"


def test_session_links_post() -> None:
    row = session_from_document(
        {
            "_social_kind": "session",
            "app_type": "sca",
            "session_id": "s-1",
            "post_id": "p-1",
            "poster_user_id": "u-owner",
            "claimer_user_id": "u-claimer",
            "scheduled_at": "2026-02-01T18:00:00Z",
            "status": "scheduled",
            "human_practice_session_id": "room-abc",
        }
    )
    assert row.post_legacy_ref == "sca:marketplace:post:p-1"
    assert row.room_name == "room-abc"
