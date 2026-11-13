"""Facts about a candidate's non-verbal behaviour, lined up with what was being said. Pure: no I/O.

Inputs are the browser's per-second samples (one batch = `(skew_ms, samples)`) and the transcript's
turns (`(seq, role, message, spoken_at)`). Nothing here decides a mark or words feedback; the output
is a plain dict the writer model is given and the candidate's read is built from.

When a turn is stamped (checked 2026-11-13). The engine's collector
(`osce_assessment/runtime/collector.py` `on_message`) stamps `timestamp = clock()` at the moment the
adapter reports the turn: for the candidate on the final speech-to-text result
(`user_input_transcribed`, `is_final`), for the patient on `conversation_item_added` once the reply
has been spoken. So a turn's `spoken_at` (api `TranscriptMessage.spoken_at`) is the END of that turn,
give or take about a second of recognition delay. A turn's window is therefore
`(previous turn's spoken_at, its own spoken_at]`; the first turn's window opens at the first sample
and the last turn's runs to the last sample. The one-to-two second lag is smaller than the
five-second spans and the three-second rule below, so it is not corrected for.

The patient is the `assistant` role (the engine's roles are `user` and `assistant`).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

PATIENT_ROLE = "assistant"
MIN_SECONDS = 60
MIN_FACE_SHARE = 0.6
OPENING_SECONDS = 30
SMILE_AT = 50
SPAN_MIN_SECONDS = 5
SPAN_MAX_GAP_MS = 3000  # a gap of up to two missing seconds does not break a run
NOTABLE_AWAY_SECONDS = 5
NOTABLE_AWAY_AFTER_PATIENT = 3
QUOTE_CHARS = 160

Batch = tuple[int, Sequence[dict[str, Any]]]
Turn = tuple[int, str, str, datetime]


def _median(values: list[int]) -> int:
    """The middle value (the upper one for an even count); 0 for none."""
    ordered = sorted(values)
    return ordered[len(ordered) // 2] if ordered else 0


def _samples(batches: Sequence[Batch]) -> list[tuple[int, dict[str, Any]]]:
    """Every sample with its corrected time in ms, oldest first, one per second of the clock."""
    skew = _median([skew_ms for skew_ms, _ in batches])
    seen: dict[int, dict[str, Any]] = {}
    for _, samples in batches:
        for sample in samples:
            seen.setdefault(int(sample["at_ms"]) + skew, sample)
    return sorted(seen.items())


def _window_index(ends: list[int], at_ms: int) -> int:
    """The turn whose window holds this time; the last turn's window runs to the end."""
    for index, end in enumerate(ends):
        if at_ms <= end:
            return index
    return len(ends) - 1


def _away_spans(
    timed: list[tuple[int, dict[str, Any]]], start_ms: int, turns: list[Turn], ends: list[int]
) -> list[dict[str, Any]]:
    """Runs of looking away of at least five seconds, each tied to the turn it started in."""
    runs: list[list[int]] = []
    for at_ms, sample in timed:
        if not (sample["face"] and sample["away"]):
            continue
        if runs and at_ms - runs[-1][-1] <= SPAN_MAX_GAP_MS:
            runs[-1].append(at_ms)
        else:
            runs.append([at_ms])
    spans = []
    for run in runs:
        duration = (run[-1] - run[0]) // 1000 + 1
        if duration < SPAN_MIN_SECONDS:
            continue
        span: dict[str, Any] = {"start_seconds": (run[0] - start_ms) // 1000, "duration_seconds": duration}
        if turns:
            seq, role, message, _ = turns[_window_index(ends, run[0])]
            span.update(seq=seq, role=role, quote=message[:QUOTE_CHARS])
        spans.append(span)
    return spans


@dataclass
class _TurnStats:
    """What was seen during one turn's window."""

    seq: int
    role: str
    seconds: int = 0
    face_seconds: int = 0
    away_seconds: int = 0
    nods: int = 0
    first_away_ms: int | None = None


def _turn_stats(
    timed: list[tuple[int, dict[str, Any]]], turns: list[Turn], ends: list[int]
) -> list[_TurnStats]:
    """Per turn: seconds in its window, face and away seconds, nods, and when the first look-away began."""
    stats = [_TurnStats(seq=seq, role=role) for seq, role, _, _ in turns]
    for at_ms, sample in timed:
        row = stats[_window_index(ends, at_ms)]
        row.seconds += 1
        row.face_seconds += bool(sample["face"])
        row.nods += bool(sample["nod"])
        if sample["face"] and sample["away"]:
            row.away_seconds += 1
            if row.first_away_ms is None:
                row.first_away_ms = at_ms
    return stats


def _notable(stats: list[_TurnStats], turns: list[Turn], start_ms: int) -> list[dict[str, Any]]:
    """Turns worth a comment: five seconds away, or a listener who looked away and did not nod."""
    out = []
    for index, (row, (seq, role, message, _)) in enumerate(zip(stats, turns, strict=True)):
        after_patient = index > 0 and role != PATIENT_ROLE and turns[index - 1][1] == PATIENT_ROLE
        away = row.away_seconds
        listened_without_nodding = after_patient and row.nods == 0 and away >= NOTABLE_AWAY_AFTER_PATIENT
        if away < NOTABLE_AWAY_SECONDS and not listened_without_nodding:
            continue
        nods = "no nods" if row.nods == 0 else f"{row.nods} nod{'s' if row.nods > 1 else ''}"
        out.append(
            {
                "seq": seq,
                "start_seconds": ((row.first_away_ms or 0) - start_ms) // 1000,
                "quote": message[:QUOTE_CHARS],
                "note": f"looked away for {away} of {row.seconds} seconds, {nods}",
            }
        )
    return out


def build_facts(batches: Sequence[Batch], turns: Sequence[Turn]) -> dict[str, Any]:
    """Turn the batches and the transcript into the facts the written section is built from.

    Samples are put on the server's clock by each batch's median skew, de-duplicated and sorted. Under
    sixty seconds of samples, or a face in under 60% of them, the result is `insufficient` and nothing
    else is worth writing from it. `start_seconds` values count from the first sample.
    """
    timed = _samples(batches)
    total = len(timed)
    face = sum(1 for _, sample in timed if sample["face"])
    facts: dict[str, Any] = {
        "seconds_total": total,
        "seconds_face": face,
        "insufficient": total < MIN_SECONDS or face / total < MIN_FACE_SHARE,
        "facing_percent": 0,
        "nods_total": sum(1 for _, sample in timed if sample["nod"]),
        "smiled_in_opening": any(sample["smile"] >= SMILE_AT for _, sample in timed[:OPENING_SECONDS]),
        "turns": [],
        "away_spans": [],
        "nods_while_patient_spoke": 0,
        "notable_turns": [],
    }
    if not total:
        return facts
    facing = sum(1 for _, sample in timed if sample["face"] and not sample["away"])
    facts["facing_percent"] = (200 * facing + face) // (2 * face) if face else 0
    ordered = sorted(turns, key=lambda turn: turn[0])
    if not ordered:
        return facts
    start_ms = timed[0][0]
    ends = [int(spoken_at.timestamp() * 1000) for _, _, _, spoken_at in ordered]
    stats = _turn_stats(timed, ordered, ends)
    facts["turns"] = [
        {
            "seq": row.seq,
            "role": row.role,
            "seconds": row.seconds,
            "face_seconds": row.face_seconds,
            "away_seconds": row.away_seconds,
            "nods": row.nods,
        }
        for row in stats
    ]
    facts["away_spans"] = _away_spans(timed, start_ms, ordered, ends)
    facts["nods_while_patient_spoke"] = sum(row.nods for row in stats if row.role == PATIENT_ROLE)
    facts["notable_turns"] = _notable(stats, ordered, start_ms)
    return facts
