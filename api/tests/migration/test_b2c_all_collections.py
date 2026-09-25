"""The pure parts of the all-collections copy: the inventory, the demo filter,
value cleaning and the legacy transcript quirks."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.migration import b2c_inventory
from app.migration.attempts import MigratedAttempt, MigratedMessage, MigratedResult
from app.migration.b2c_firestore import is_seed, serialize
from app.migration.b2c_lookups import StepReport
from app.migration.b2c_transcript_cleanup import clean, message_key

T0 = datetime(2026, 4, 25, 10, 0, tzinfo=UTC)


def _turn(message_id: str, text: str, minute: int) -> MigratedMessage:
    return MigratedMessage(message_id, 0, "user", text, T0 + timedelta(minutes=minute))


def _attempt(messages: list[MigratedMessage], *, result: bool = False) -> MigratedAttempt:
    return MigratedAttempt(
        legacy_ids={"attempt_id": "att-1"},
        exam_code="sca",
        kind="practice",
        user_ref="usr_1",
        created_at=T0,
        status="evaluated" if result else "interaction_complete",
        messages=messages,
        result=MigratedResult("sca-legacy", "legacy-b2c", {}) if result else None,
    )


def test_every_live_collection_must_be_copied_or_skipped_with_a_reason() -> None:
    assert b2c_inventory.step_for("comments") == "community"
    assert b2c_inventory.step_for("plab_transcripts") == "attempts"
    assert b2c_inventory.skip_reason("b2b_slots_v1")
    assert b2c_inventory.unaccounted(["comments", "b2b_slots_v1", "brand_new"]) == ["brand_new"]


def test_demo_rows_are_recognised_by_tag_or_seed_owner() -> None:
    assert is_seed({"_seed_tag": "demo"})
    assert is_seed({"user_id": "seed_user_3"})
    assert is_seed({"created_by": "seed_admin"})
    assert not is_seed({"user_id": "usr_1", "created_by": "y-hkehinde"})


def test_nul_characters_are_dropped_because_postgres_refuses_them() -> None:
    assert serialize({"a": ["x\x00y"], "b": "ok"}) == {"a": ["xy"], "b": "ok"}


def test_a_re_sent_turn_keeps_its_first_position_and_its_later_text() -> None:
    attempt = _attempt(
        [_turn("m1", "hello", 0), _turn("m2", "typo", 1), _turn("m3", "bye", 2), _turn("m2", "fixed", 3)]
    )
    report = StepReport()
    ((out, _raw),) = clean([(attempt, {})], report)
    assert [(m.message_id, m.message, m.seq) for m in out.messages] == [
        ("m1", "hello", 0),
        ("m2", "fixed", 1),
        ("m3", "bye", 2),
    ]
    assert report.counts["re-sent transcript turns merged"] == 1


def test_an_over_long_message_id_becomes_a_stable_hash() -> None:
    broken = "637db80f-c330-4219-84a8-a06d6602ecdb! Skill categories evaluation: {..."
    assert message_key(broken) == message_key(broken)
    assert message_key(broken).startswith("legacy-") and len(message_key(broken)) <= 64
    assert message_key("m1") == "m1"


def test_a_double_saved_attempt_becomes_one_keeping_the_one_with_feedback() -> None:
    first = _attempt([_turn("a", "one", 0), _turn("c", "three", 2)])
    second = _attempt([_turn("b", "two", 1)], result=True)
    report = StepReport()
    merged = clean([(first, {"id": "doc-1"}), (second, {"id": "doc-2"})], report)
    assert len(merged) == 1
    kept, raw = merged[0]
    assert raw == {"id": "doc-2"} and kept.result is not None
    assert [(m.message_id, m.seq) for m in kept.messages] == [("a", 0), ("b", 1), ("c", 2)]
    assert report.counts["double-saved transcripts merged"] == 1
