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
    if len(message_id) <= 64:
        return message_id
    return f"legacy-{hashlib.sha256(message_id.encode()).hexdigest()[:16]}"


def _richest(pairs: Sequence[Pair]) -> Pair:
    return max(pairs, key=lambda p: (p[0].result is not None, len(p[0].messages), p[0].created_at))


def _merge_saves(pairs: Sequence[Pair], report: StepReport) -> list[Pair]:
    groups: dict[str, list[Pair]] = {}
    for pair in pairs:
        groups.setdefault(legacy_ref_for(pair[0]) or f"unkeyed:{id(pair)}", []).append(pair)
    out: list[Pair] = []
    for group in groups.values():
        if len(group) == 1:
            out.append(group[0])
            continue
        migrated, raw = _richest(group)
        migrated.messages = sorted((m for p in group for m in p[0].messages), key=lambda m: m.spoken_at)
        report.count("double-saved transcripts merged", len(group) - 1)
        out.append((migrated, raw))
    return out


def _clean_turns(migrated: MigratedAttempt, report: StepReport) -> None:
    latest: dict[str, MigratedMessage] = {}
    for message in migrated.messages:
        latest[message_key(message.message_id)] = message
    report.count("re-sent transcript turns merged", len(migrated.messages) - len(latest))
    migrated.messages = [replace(m, message_id=k, seq=i) for i, (k, m) in enumerate(latest.items())]


def clean(pairs: Sequence[Pair], report: StepReport) -> list[Pair]:
    merged = _merge_saves(pairs, report)
    for migrated, _raw in merged:
        _clean_turns(migrated, report)
    return merged
