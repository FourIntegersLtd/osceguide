"""Legacy transcript quirks, straightened out before anything is loaded.

- **Double saves.** A few attempts were saved as two Firestore transcripts with
  the same attempt id (a reconnect): same user, station and exam, no shared
  turns. They become one attempt, keeping the document with feedback or the
  most turns, with the turns of both in spoken order.
- **Re-sent turns.** Many transcripts carry the same `transcript_message_id`
  twice, most with identical text and some with the wording corrected. One row
  per id is kept, with the later text, at the first position (when it was
  spoken).
- **Broken ids.** One id has model output pasted onto it; an id too long for
  the column becomes a stable hash of itself.

`seq` is renumbered afterwards so it stays contiguous.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import replace
from typing import Any

from app.migration.attempts import MigratedAttempt, MigratedMessage
from app.migration.b2c_lookups import StepReport
from app.migration.load_attempts import legacy_ref_for

Pair = tuple[MigratedAttempt, dict[str, Any]]


def message_key(message_id: str) -> str:
    """The id to dedupe a turn on: the legacy id itself, or a stable hash if it is too long to store."""
    if len(message_id) <= 64:
        return message_id
    return f"legacy-{hashlib.sha256(message_id.encode()).hexdigest()[:16]}"


def _richest(pairs: Sequence[Pair]) -> Pair:
    """Of several double-saved copies of the same attempt, the one worth keeping.

    Preferred in order: has feedback, then has the most turns, then was saved latest.
    """
    return max(
        pairs,
        key=lambda pair: (pair[0].result is not None, len(pair[0].messages), pair[0].created_at),
    )


def _merge_saves(pairs: Sequence[Pair], report: StepReport) -> list[Pair]:
    """Collapse attempts saved as two Firestore transcripts (a reconnect) into one, turns merged in order."""
    groups: dict[str, list[Pair]] = {}
    for pair in pairs:
        groups.setdefault(legacy_ref_for(pair[0]) or f"unkeyed:{id(pair)}", []).append(pair)
    merged_pairs: list[Pair] = []
    for group in groups.values():
        if len(group) == 1:
            merged_pairs.append(group[0])
            continue
        migrated, raw = _richest(group)
        migrated.messages = sorted(
            (message for pair in group for message in pair[0].messages), key=lambda message: message.spoken_at
        )
        report.count("double-saved transcripts merged", len(group) - 1)
        merged_pairs.append((migrated, raw))
    return merged_pairs


def _clean_turns(migrated: MigratedAttempt, report: StepReport) -> None:
    """Keep one turn per re-sent `message_id` (the later text), and renumber `seq` to stay contiguous."""
    latest: dict[str, MigratedMessage] = {}
    for message in migrated.messages:
        latest[message_key(message.message_id)] = message
    report.count("re-sent transcript turns merged", len(migrated.messages) - len(latest))
    migrated.messages = [
        replace(message, message_id=key, seq=index) for index, (key, message) in enumerate(latest.items())
    ]


def clean(pairs: Sequence[Pair], report: StepReport) -> list[Pair]:
    """Merge double-saved transcripts and dedupe re-sent turns, in that order."""
    merged = _merge_saves(pairs, report)
    for migrated, _raw in merged:
        _clean_turns(migrated, report)
    return merged
