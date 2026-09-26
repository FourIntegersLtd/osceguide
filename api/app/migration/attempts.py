"""Turning legacy transcripts and feedback into attempts.

The decision recorded as D-5: b2c's production scoring path is
`feedback_generation_legacy.py`, not the engine — `FEEDBACK_ENGINE_SCORING`
defaults off — so imported feedback is tagged `legacy-b2c` and is never
silently compared with engine output.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.migration.users import UnknownLegacyProduct, exam_for_product, parse_timestamp

# What b2c's existing feedback was actually produced by.
LEGACY_POLICY_VERSION = "legacy-b2c"

__all__ = [
    "LEGACY_POLICY_VERSION",
    "MigratedAttempt",
    "MigratedMessage",
    "MigratedResult",
    "UnknownLegacyProduct",
    "attempt_from_transcript",
]


@dataclass(frozen=True)
class MigratedMessage:
    """One transcript turn, ready for `TranscriptMessage`."""

    message_id: str
    seq: int
    role: str
    message: str
    spoken_at: datetime


@dataclass(frozen=True)
class MigratedResult:
    """The legacy feedback for an attempt, tagged so it is never mistaken for engine output."""

    framework_id: str
    policy_version: str
    payload: dict[str, Any]


@dataclass
class MigratedAttempt:
    """One consumer practice attempt, its turns and its legacy feedback, ready for `load_attempts`."""

    legacy_ids: dict[str, str]
    exam_code: str
    kind: str
    user_ref: str
    created_at: datetime
    status: str
    failed_reason: str | None = None
    # The imported station-set entry this ran against, once the sets are
    # migrated. Null means the attempt is loaded as plain practice.
    set_entry_ref: str | None = None
    messages: list[MigratedMessage] = field(default_factory=list)
    result: MigratedResult | None = None


def _message_id(attempt_ref: str, index: int, transcript_document: dict[str, Any]) -> str:
    """The turn's own id, or a stable one derived from where it sits.

    Older rows predate the field. Deriving it from the attempt and position
    means re-running the import produces the same ids, so the unique constraint
    on `(attempt_id, message_id)` makes a second run a no-op rather than a
    duplicate.
    """
    existing = str(transcript_document.get("transcript_message_id") or "").strip()
    if existing:
        return existing
    digest = hashlib.sha256(f"{attempt_ref}:{index}".encode()).hexdigest()
    return f"legacy-{digest[:16]}"


def attempt_from_transcript(
    transcript_document: dict[str, Any],
    *,
    app_type: str,
    feedback: dict[str, Any] | None = None,
    framework_id: str = "",
    set_entry_ref: str | None = None,
) -> MigratedAttempt:
    """Turn one legacy transcript into an attempt.

    `set_entry_ref` names the imported station-set entry this ran against, if
    the sets have been migrated. Without one the attempt is `practice`, not
    `set_station`: the schema requires a `set_entry_id` for `set_station` —
    an attempt with no entry is not one — and claiming the kind while leaving
    the reference null is how b2b ended up with columns that mean nothing.
    The legacy `mock_id` and `station_id` are kept either way, so the linkage
    can be restored when the sets come across.
    """
    exam_code = exam_for_product(app_type)
    attempt_ref = str(transcript_document.get("attempt_id") or transcript_document.get("transcript_id") or "")

    messages = [
        MigratedMessage(
            message_id=_message_id(attempt_ref, index, entry),
            seq=index,
            role=str(entry.get("role") or "user"),
            message=str(entry.get("message") or ""),
            spoken_at=parse_timestamp(entry.get("timestamp")) or datetime.now(UTC),
        )
        for index, entry in enumerate(transcript_document.get("transcript_message") or [])
    ]

    if not messages:
        # Nothing to mark, and importing it as complete would queue scoring for
        # a session that never happened.
        status, failed_reason, result = "failed", "empty_transcript", None
    elif feedback:
        status, failed_reason = "evaluated", None
        result = MigratedResult(
            framework_id=framework_id or f"{exam_code}-legacy",
            policy_version=LEGACY_POLICY_VERSION,
            payload=feedback,
        )
    else:
        status, failed_reason, result = "interaction_complete", None, None

    return MigratedAttempt(
        legacy_ids={
            "transcript_id": str(transcript_document.get("transcript_id") or ""),
            "mock_id": str(transcript_document.get("mock_id") or ""),
            "station_id": str(transcript_document.get("station_id") or ""),
            "attempt_id": str(transcript_document.get("attempt_id") or ""),
        },
        exam_code=exam_code,
        kind="set_station" if set_entry_ref else "practice",
        set_entry_ref=set_entry_ref,
        user_ref=str(transcript_document.get("user_id") or ""),
        created_at=parse_timestamp(transcript_document.get("created_at")) or datetime.now(UTC),
        status=status,
        failed_reason=failed_reason,
        messages=messages,
        result=result,
    )
