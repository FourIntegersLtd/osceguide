"""The parity harness understands all three stored transcript shapes."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from parity_run import normalise, shape_report, to_engine_transcript  # noqa: E402

LEGACY_B2C = {"transcript_message": [{"role": "user", "message": "Hi"}, {"role": "assistant", "message": "Hello"}]}
LEGACY_B2B = [{"role": "trainee", "message": "Hi"}, {"role": "ai_patient", "message": "Hello"}, {"role": "trainee", "message": "  "}]
ENGINE = {"attempt_id": "a", "messages": [{"role": "user", "message": "Hi"}, {"role": "assistant", "message": "Hello"}]}


def test_all_shapes_normalise_to_the_same_turns() -> None:
    assert normalise(LEGACY_B2C) == normalise(LEGACY_B2B) == normalise(ENGINE) == [("user", "Hi"), ("assistant", "Hello")]
    assert normalise({"transcript": ENGINE}) == normalise(ENGINE)


def test_shape_report_and_engine_transcript() -> None:
    report = shape_report("x", normalise(ENGINE))
    assert (report["turns"], report["user_turns"], report["assistant_turns"], report["alternates"], report["starts_with"]) == (2, 1, 1, True, "user")
    transcript = to_engine_transcript("a", normalise(ENGINE))
    assert [m.seq for m in transcript.messages] == [0, 1] and transcript.complete
