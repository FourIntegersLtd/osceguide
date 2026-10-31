"""The stored shape of a compacted transcript round-trips exactly."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta, timezone

from app.features.attempts.domain import Turn, from_document, to_document

AT = datetime(2026, 10, 31, 12, 0, 0, 123456, tzinfo=UTC)


def turns() -> list[Turn]:
    return [
        Turn("m0", 0, "patient", 'He said "no", then\nleft: café ½ \U0001f600', AT),
        Turn("m1", 1, "doctor", "", AT + timedelta(microseconds=1)),
        Turn("m2", 2, "patient", "tab\there \\ backslash", AT + timedelta(seconds=90)),
    ]


def test_the_document_has_the_versioned_readable_shape() -> None:
    doc = to_document(turns()[:1])

    assert doc == {
        "v": 1,
        "turns": [
            {
                "message_id": "m0",
                "seq": 0,
                "role": "patient",
                "message": 'He said "no", then\nleft: café ½ \U0001f600',
                "spoken_at": "2026-10-31T12:00:00.123456+00:00",
            }
        ],
    }


def test_a_round_trip_through_json_returns_every_field_unchanged() -> None:
    original = turns()

    restored = from_document(json.loads(json.dumps(to_document(original))))

    assert restored == original
    assert [t.spoken_at.microsecond for t in restored] == [123456, 123457, 123456]


def test_seq_order_is_kept_as_given() -> None:
    original = [Turn("b", 5, "doctor", "x", AT), Turn("a", 9, "patient", "y", AT)]

    assert [t.seq for t in from_document(to_document(original))] == [5, 9]


def test_a_non_utc_time_comes_back_as_the_same_instant() -> None:
    plus_two = datetime(2026, 10, 31, 14, 0, 0, 5, tzinfo=timezone(timedelta(hours=2)))

    restored = from_document(to_document([Turn("m", 0, "doctor", "x", plus_two)]))

    assert restored[0].spoken_at == plus_two
    assert restored[0].spoken_at.utcoffset() == timedelta(0)
