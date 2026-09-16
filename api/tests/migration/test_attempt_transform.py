"""Turning b2c transcripts and feedback into attempts.

The decision recorded as D-5: existing consumer feedback came from the legacy
scorer, not the engine, because `FEEDBACK_ENGINE_SCORING` defaults off. It is
imported tagged `legacy-b2c` so it is never silently compared with engine output.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.migration import attempts as transform

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


def transcript(**overrides: object) -> dict:
    return {
        "transcript_id": "t-1",
        "user_id": "u-1",
        "mock_id": "m-1",
        "station_id": "s-1",
        "attempt_id": "a-1",
        "created_at": "2026-05-01T10:00:00Z",
        "transcript_message": [
            {
                "role": "user",
                "message": "Hello doctor",
                "timestamp": "2026-05-01T10:00:05Z",
                "transcript_message_id": "m0",
            },
            {
                "role": "assistant",
                "message": "Tell me more",
                "timestamp": "2026-05-01T10:00:10Z",
                "transcript_message_id": "m1",
            },
        ],
        **overrides,
    }


def test_a_transcript_becomes_an_attempt_with_its_turns() -> None:
    attempt = transform.attempt_from_transcript(transcript(), app_type="sca")
    assert attempt.exam_code == "sca"
    # `practice`, not `set_station`, because no set entry was supplied. The
    # schema requires a `set_entry_id` for `set_station`; an attempt with no
    # entry is not one.
    assert attempt.kind == "practice"
    assert [m.seq for m in attempt.messages] == [0, 1]
    assert attempt.messages[0].role == "user"


def test_the_legacy_message_id_is_preserved() -> None:
    """It is the idempotency key for chunks, so it has to survive the import or
    a redelivery would duplicate turns."""
    attempt = transform.attempt_from_transcript(transcript(), app_type="sca")
    assert [m.message_id for m in attempt.messages] == ["m0", "m1"]


def test_turns_without_an_id_are_given_a_stable_one() -> None:
    """Older rows predate the field. Derived from the attempt and position, so
    re-running the import produces the same ids rather than duplicates."""
    raw = transcript(
        transcript_message=[{"role": "user", "message": "Hi", "timestamp": "2026-05-01T10:00:05Z"}]
    )
    first = transform.attempt_from_transcript(raw, app_type="sca")
    second = transform.attempt_from_transcript(raw, app_type="sca")
    assert first.messages[0].message_id == second.messages[0].message_id
    assert first.messages[0].message_id


def test_an_empty_transcript_is_marked_failed_rather_than_imported_as_complete() -> None:
    """There is nothing to mark, and importing it as complete would queue
    scoring for a session that never happened."""
    attempt = transform.attempt_from_transcript(transcript(transcript_message=[]), app_type="sca")
    assert attempt.status == "failed"
    assert attempt.failed_reason == "empty_transcript"


def test_a_complete_transcript_is_evaluated_when_feedback_exists() -> None:
    attempt = transform.attempt_from_transcript(transcript(), app_type="sca", feedback={"overall": "G"})
    assert attempt.status == "evaluated"
    assert attempt.result is not None


def test_legacy_feedback_is_tagged_as_legacy() -> None:
    """D-5. b2c's production scorer was not the engine, so this must never be
    silently compared with engine output — the dashboard segments on it."""
    attempt = transform.attempt_from_transcript(transcript(), app_type="sca", feedback={"overall": "G"})
    assert attempt.result is not None
    assert attempt.result.policy_version == "legacy-b2c"


def test_a_transcript_without_feedback_stops_at_interaction_complete() -> None:
    attempt = transform.attempt_from_transcript(transcript(), app_type="sca")
    assert attempt.status == "interaction_complete"
    assert attempt.result is None


def test_an_unknown_product_stops_the_import() -> None:
    with pytest.raises(transform.UnknownLegacyProduct):
        transform.attempt_from_transcript(transcript(), app_type="mrcp")


def test_the_legacy_ids_are_carried_for_reconciliation() -> None:
    """The verify step compares counts against the export, which needs the old
    identifiers to match rows up."""
    attempt = transform.attempt_from_transcript(transcript(), app_type="sca")
    assert attempt.legacy_ids == {
        "transcript_id": "t-1",
        "mock_id": "m-1",
        "station_id": "s-1",
        "attempt_id": "a-1",
    }


def test_a_transcript_with_an_imported_set_entry_is_a_set_station() -> None:
    attempt = transform.attempt_from_transcript(transcript(), app_type="sca", set_entry_ref="entry-1")
    assert attempt.kind == "set_station"
    assert attempt.set_entry_ref == "entry-1"
