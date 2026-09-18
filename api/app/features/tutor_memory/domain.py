"""What the tutor may remember, and the rules about remembering it.

Plain Python: no SQL, no FastAPI, no I/O. Everything here answers a question
about memory that has one right answer regardless of where the rows live —
whether an activity is the same one twice, how long ago something was, which
kinds of conversation are worth keeping, and what a tool call is allowed to
ask for.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

# Two sightings of the same thing inside this window are one visit. A doctor
# who opens a summary, follows a link and comes back has not read it twice, and
# a memory that says they did will be spoken back to them as a pattern.
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

    Replaces the plain "help sessions only" rule: once a dashboard session is
    the tutor's memory of a conversation, discarding it unread would lose the
    one thing worth keeping, and retaining it would keep a recording nobody
    asked for. An unknown type discards, which is the safe side to err on.
    """
    return _POLICIES.get((session_type or "").strip().lower(), TranscriptPolicy.DISCARD)


def should_record_event(*, last_seen_at: datetime | None, now: datetime) -> bool:
    """Whether this sighting is a new visit rather than the same one again."""
    if last_seen_at is None:
        return True
    return (now - last_seen_at) >= DEDUP_WINDOW


def days_ago(then: datetime, now: datetime) -> int:
    """Whole days between two moments, never negative.

    The tutor says "about a week ago", never a date, so this is all the
    precision the brief carries. A clock that has drifted backwards reads as
    today rather than as the future.
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

    Only a debrief: it is the conversation where the doctor and the tutor
    agreed something, and the agreement is what the tutor needs next time. A
    consultation's own marking is already a result.
    """
    return kind == "debrief" and complete


def entitled_exam_ids(grants: Sequence[Any]) -> frozenset[Any]:
    """The exams this person may be shown material from.

    Suggestions are filtered through this before anything is named, so a
    refusal never mentions the title of something they cannot open — which is
    how a locked item becomes an advertisement.
    """
    return frozenset(getattr(g, "exam_id", None) for g in grants if getattr(g, "exam_id", None))


def open_action_items(plans: Sequence[Any]) -> list[str]:
    """Steps that were agreed and not yet ticked off, most recent first.

    Accepts both shapes the summariser produces: `{"text": ..., "done": ...}`
    and a bare string, which is what the model returns when it ignores the
    schema's optional flag.
    """
    out: list[str] = []
    for plan in plans:
        items = plan if isinstance(plan, Sequence) and not isinstance(plan, str) else []
        for item in items:
            if isinstance(item, Mapping):
                if item.get("done"):
                    continue
                text = str(item.get("text") or "").strip()
            else:
                text = str(item or "").strip()
            if text:
                out.append(text)
    return out


def observations_from_result(payload: Mapping[str, Any]) -> dict[str, Any]:
    """What a marking says about a consultation, in the brief's own vocabulary.

    The engine's result payload is a marking document: domains with ratings,
    strengths, improvements, and phrases the doctor actually used. The brief
    wants exactly those four, named the way the tutor prompt reads them, and
    nothing else — no scores, no percentages, no identifiers, because the
    prompt forbids the tutor from saying any of them out loud.
    """
    domains: dict[str, str] = {}
    for entry in _sequence(payload.get("domains")):
        if not isinstance(entry, Mapping):
            continue
        name = str(entry.get("name") or entry.get("domain") or "").strip()
        rating = str(entry.get("rating") or entry.get("grade") or "").strip()
        if name and rating:
            domains[name] = rating
    if not domains and isinstance(payload.get("domains"), Mapping):
        domains = {str(k): str(v) for k, v in payload["domains"].items() if str(v or "").strip()}

    return {
        "domains": domains,
        "strengths": _texts(payload.get("strengths") or payload.get("what_went_well")),
        "improvements": _texts(payload.get("improvements") or payload.get("areas_for_improvement")),
        "phrases": _texts(payload.get("phrases") or payload.get("quotes")),
    }


def validate_tool_arguments(schema: Mapping[str, Any], arguments: Mapping[str, Any]) -> dict[str, Any]:
    """Check one tool call against its own advertised schema.

    Deliberately small: the schemas are ours, they are flat objects of strings,
    enums and small integers, and a validator library would be a dependency
    carrying rules nothing here uses. What it must catch is a model inventing
    an argument or a value — the tutor calling `recall_history` with a kind
    that means nothing produces an answer about the wrong thing.
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
        raise InvalidToolArguments(f"{name} must be one of: {', '.join(str(a) for a in allowed)}")
    limit = spec.get("maxLength")
    if limit is not None and len(text) > int(limit):
        text = text[: int(limit) - 1].rstrip() + "…"
    return text


def _sequence(value: Any) -> list[Any]:
    if isinstance(value, Sequence) and not isinstance(value, str):
        return list(value)
    return []


def _texts(value: Any) -> list[str]:
    out: list[str] = []
    for item in _sequence(value):
        text = str(item.get("text") if isinstance(item, Mapping) else item or "").strip()
        if text:
            out.append(text)
    return out
