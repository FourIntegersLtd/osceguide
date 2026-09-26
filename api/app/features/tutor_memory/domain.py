"""What the tutor may remember, and the rules about remembering it.

Plain Python: no SQL, no FastAPI, no I/O.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

# Two sightings of the same thing inside this window are one visit. A doctor
# who opens a summary, follows a link and comes back has not read it twice, and
# a memory that says they did will be spoken back to them as a pattern.
# Re-exported so callers import one domain.
from app.features.tutor_memory.action_plan import mark_action_item_done, open_action_items

__all__ = ["mark_action_item_done", "open_action_items"]

DEDUP_WINDOW = timedelta(minutes=10)

# A stated fact is spoken back to the doctor; a long one stops being a fact and
# becomes a paragraph the tutor recites.
MAX_FACT_CHARS = 300

EVENT_KINDS = frozenset({"viewed", "practised", "listened"})
REF_KINDS = frozenset({"summary", "slide_deck", "podcast", "blog", "station", "management_plan"})
NOTE_KINDS = frozenset({"session_summary", "stated_fact"})


class InvalidToolArguments(ValueError):
    """A tool was called with arguments its schema does not allow."""


class TranscriptPolicy(StrEnum):
    """What becomes of a conversation once it ends."""

    RETAIN = "retain"
    SUMMARISE = "summarise"
    DISCARD = "discard"


# A help session's turns are kept as they were: they are a record of somebody
# reporting a problem. A dashboard session is summarised and then deleted —
# what the tutor needs next time is what was agreed, not a recording of the
# conversation. Everything else is navigation and is discarded unread.
_POLICIES = {
    "help": TranscriptPolicy.RETAIN,
    "dashboard": TranscriptPolicy.SUMMARISE,
    "onboarding": TranscriptPolicy.DISCARD,
    "consulting-doctor": TranscriptPolicy.DISCARD,
}


def transcript_policy(session_type: str) -> TranscriptPolicy:
    """What to do with this kind of session's turns when it ends.

    An unknown type discards, which is the safe side to err on.
    """
    return _POLICIES.get((session_type or "").strip().lower(), TranscriptPolicy.DISCARD)


def should_record_event(*, last_seen_at: datetime | None, now: datetime) -> bool:
    """Whether this sighting is a new visit rather than the same one again."""
    if last_seen_at is None:
        return True
    return (now - last_seen_at) >= DEDUP_WINDOW


def days_ago(then: datetime, now: datetime) -> int:
    """Whole days between two moments, never negative.

    A clock that has drifted backwards reads as today rather than as the future.
    """
    return max(0, (now - then).days)


def clip_fact(text: str) -> str:
    """One remembered fact, trimmed to something sayable."""
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= MAX_FACT_CHARS:
        return cleaned
    return cleaned[: MAX_FACT_CHARS - 1].rstrip() + "…"


def should_summarise_attempt(*, kind: str, complete: bool) -> bool:
    """Whether a finished attempt is worth writing a debrief summary of.

    Only a debrief: a consultation's own marking is already a result.
    """
    return kind == "debrief" and complete


def entitled_exam_ids(grants: Sequence[Any]) -> frozenset[Any]:
    """The exams this person may be shown material from, right now.

    `entitlements.service.list_for_user` returns every row ever held, revoked or
    expired included, and computes `live` per row rather than filtering. Reading
    `exam_id` off every grant without checking `live` previously handed a lapsed
    subscriber the same access as a paying one. A grant that cannot say whether
    it is live is excluded, so an unrecognised row loses access rather than gains it.
    """
    return frozenset(
        getattr(grant, "exam_id", None)
        for grant in grants
        if getattr(grant, "exam_id", None) and getattr(grant, "live", False)
    )


def observations_from_result(marking_result: Mapping[str, Any]) -> dict[str, Any]:
    """What a marking says about a consultation, in the brief's own vocabulary.

    Extracts domains, strengths, improvements and phrases only — no scores,
    percentages or identifiers, since the tutor prompt forbids saying those aloud.
    """
    domains: dict[str, str] = {}
    for entry in _sequence(marking_result.get("domains")):
        if not isinstance(entry, Mapping):
            continue
        name = str(entry.get("name") or entry.get("domain") or "").strip()
        rating = str(entry.get("rating") or entry.get("grade") or "").strip()
        if name and rating:
            domains[name] = rating
    if not domains and isinstance(marking_result.get("domains"), Mapping):
        domains = {
            str(domain_name): str(rating)
            for domain_name, rating in marking_result["domains"].items()
            if str(rating or "").strip()
        }

    return {
        "domains": domains,
        "strengths": _texts(marking_result.get("strengths") or marking_result.get("what_went_well")),
        "improvements": _texts(
            marking_result.get("improvements") or marking_result.get("areas_for_improvement")
        ),
        "phrases": _texts(marking_result.get("phrases") or marking_result.get("quotes")),
    }


def validate_tool_arguments(schema: Mapping[str, Any], arguments: Mapping[str, Any]) -> dict[str, Any]:
    """Check one tool call's arguments against its own advertised schema.

    Catches a model inventing an argument or a value the schema doesn't allow.
    """
    properties = schema.get("properties") or {}
    required = schema.get("required") or []
    unknown = sorted(set(arguments) - set(properties))
    if unknown:
        raise InvalidToolArguments(f"unknown argument(s): {', '.join(unknown)}")
    missing = sorted(name for name in required if not str(arguments.get(name) or "").strip())
    if missing:
        raise InvalidToolArguments(f"missing argument(s): {', '.join(missing)}")

    cleaned: dict[str, Any] = {}
    for name, value in arguments.items():
        spec = properties[name] if isinstance(properties.get(name), Mapping) else {}
        cleaned[name] = _coerce(name, value, spec)
    return cleaned


def _coerce(name: str, value: Any, spec: Mapping[str, Any]) -> Any:
    """One argument, converted and range- or length-checked against its schema entry."""
    declared = spec.get("type")
    if declared == "integer":
        try:
            number = int(value)
        except (TypeError, ValueError) as exc:
            raise InvalidToolArguments(f"{name} must be a whole number") from exc
        low, high = spec.get("minimum"), spec.get("maximum")
        if low is not None and number < int(low):
            raise InvalidToolArguments(f"{name} must be at least {low}")
        if high is not None and number > int(high):
            raise InvalidToolArguments(f"{name} must be at most {high}")
        return number

    text = " ".join(str(value or "").split())
    allowed = spec.get("enum")
    if allowed and text not in allowed:
        raise InvalidToolArguments(f"{name} must be one of: {', '.join(str(choice) for choice in allowed)}")
    limit = spec.get("maxLength")
    if limit is not None and len(text) > int(limit):
        text = text[: int(limit) - 1].rstrip() + "…"
    return text


def _sequence(value: Any) -> list[Any]:
    """`value` as a list, or empty if it isn't a sequence (a bare string doesn't count)."""
    if isinstance(value, Sequence) and not isinstance(value, str):
        return list(value)
    return []


def _texts(value: Any) -> list[str]:
    """Plain strings out of a list that may hold bare strings or `{"text": ...}` entries."""
    texts: list[str] = []
    for entry in _sequence(value):
        text = str(entry.get("text") if isinstance(entry, Mapping) else entry or "").strip()
        if text:
            texts.append(text)
    return texts
