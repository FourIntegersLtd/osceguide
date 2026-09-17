"""Render what a tutor remembers about one learner as spoken-friendly prose.

The brief is a plain dict the consumer assembles; nothing here knows where a
consultation, a debrief or a note came from. Every number is written as it is
said, ratings are words rather than letters, and hard caps keep the rendered
text inside a fixed token budget however much history the learner has.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

MAX_CONSULTATIONS = 6
MAX_DEBRIEFS = 3
MAX_ACTIVITIES = 8
MAX_FACTS = 5
MAX_ITEMS_EACH = 3
MAX_SNIPPET_CHARS = 160

RATING_WORDS = {"r": "needs work", "a": "competent", "g": "strong", "red": "needs work", "amber": "competent", "green": "strong"}
SMALL_NUMBERS = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve")


def number_word(n: int) -> str:
    return SMALL_NUMBERS[n] if 0 <= n < len(SMALL_NUMBERS) else str(n)


def when(days_ago: Any) -> str:
    """How long ago, the way a person says it. Unknown stays unknown rather than guessed."""
    try:
        days = int(days_ago)
    except (TypeError, ValueError):
        return "recently"
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 7:
        return f"{number_word(days)} days ago"
    if days < 14:
        return "about a week ago"
    if days < 28:
        return f"about {number_word(days // 7)} weeks ago"
    if days < 60:
        return "about a month ago"
    return f"about {number_word(days // 30)} months ago"


def rating_word(value: Any) -> str:
    return RATING_WORDS.get(str(value or "").strip().lower(), "")


def snippet(text: Any) -> str:
    cleaned = " ".join(str(text or "").split())
    return cleaned if len(cleaned) <= MAX_SNIPPET_CHARS else cleaned[: MAX_SNIPPET_CHARS - 1].rstrip() + "…"


def _strings(items: Any, limit: int = MAX_ITEMS_EACH) -> list[str]:
    if not isinstance(items, Sequence) or isinstance(items, str):
        return []
    out: list[str] = []
    for item in items:
        text = item.get("text") if isinstance(item, Mapping) else item
        if str(text or "").strip():
            out.append(snippet(text))
        if len(out) == limit:
            break
    return out


def _sentence_list(items: Sequence[str]) -> str:
    items = list(items)
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def render_consultation(item: Mapping[str, Any]) -> str:
    title = snippet(item.get("title")) or "a consultation"
    lines = [f"{title}, {when(item.get('days_ago'))}."]
    domains = item.get("domains")
    if isinstance(domains, Mapping):
        rated = [f"{name} {rating_word(value)}" for name, value in domains.items() if rating_word(value)]
        if rated:
            lines.append(f"How it went: {_sentence_list(rated)}.")
    strengths = _strings(item.get("strengths"), 1)
    if strengths:
        lines.append(f"What went well: {strengths[0]}")
    improvements = _strings(item.get("improvements"))
    if improvements:
        lines.append(f"Worth working on: {_sentence_list(improvements)}")
    phrases = _strings(item.get("phrases"), 1)
    if phrases:
        lines.append(f'Something they said: "{phrases[0]}"')
    return "\n".join(lines)


def render_debrief(item: Mapping[str, Any]) -> str:
    title = snippet(item.get("title")) or "a consultation"
    lines = [f"Debrief on {title}, {when(item.get('days_ago'))}."]
    insights = _strings(item.get("insights"))
    if insights:
        lines.append(f"What you both noticed: {_sentence_list(insights)}")
    steps = _strings(item.get("agreed_steps"))
    if steps:
        lines.append(f"What was agreed: {_sentence_list(steps)}")
    return "\n".join(lines)


def render_activity(item: Mapping[str, Any]) -> str:
    verb = {"read": "read", "practised": "practised", "listened": "listened to", "viewed": "read"}.get(str(item.get("kind") or "").lower(), "looked at")
    title = snippet(item.get("title")) or "something"
    return f"{verb} {title}, {when(item.get('days_ago'))}"


def render_last_conversation(item: Mapping[str, Any]) -> str:
    lines = [f"You last spoke {when(item.get('days_ago'))}."]
    summary = snippet(item.get("summary"))
    if summary:
        lines.append(summary)
    steps = _strings(item.get("agreed_next_steps"))
    if steps:
        lines.append(f"You agreed they would: {_sentence_list(steps)}")
    return "\n".join(lines)


def render_brief(brief: Mapping[str, Any]) -> str:
    """The whole memory, or a line saying there is none. Never a claim the data does not make."""
    parts: list[str] = []
    consultations = [render_consultation(c) for c in _maps(brief.get("consultations"))[:MAX_CONSULTATIONS]]
    if consultations:
        parts.append("Their recent consultations, most recent first:\n\n" + "\n\n".join(consultations))
    debriefs = [render_debrief(d) for d in _maps(brief.get("debriefs"))[:MAX_DEBRIEFS]]
    if debriefs:
        parts.append("Debriefs you have had together:\n\n" + "\n\n".join(debriefs))
    last = brief.get("last_conversation")
    if isinstance(last, Mapping):
        parts.append("Your last conversation:\n" + render_last_conversation(last))
    facts = _strings(brief.get("facts"), MAX_FACTS)
    if facts:
        parts.append("Things they have told you:\n" + "\n".join(f"They said: {f}" for f in facts))
    activity = [render_activity(a) for a in _maps(brief.get("activity"))[:MAX_ACTIVITIES]]
    if activity:
        parts.append("What they have been reading and practising:\n" + "\n".join(f"They {a}." for a in activity))
    if not parts:
        return (
            "You have nothing on file about this doctor yet. Do not pretend otherwise: ask what they have "
            "been practising and what they would like from today, and remember what they tell you."
        )
    return "\n\n".join(parts)


def _maps(items: Any) -> list[Mapping[str, Any]]:
    if not isinstance(items, Sequence) or isinstance(items, str):
        return []
    return [i for i in items if isinstance(i, Mapping)]
