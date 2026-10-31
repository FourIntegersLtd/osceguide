"""Writes what Ben says for each moment of a slide, so the words and the slide cannot drift.

A slide with bullets is narrated as an `intro` (spoken over the title alone) and one line per
bullet, in the order the bullets appear (a main bullet, then its sub-bullets). The renderer
shows a bullet exactly when its line starts, so alignment holds by construction.

`plan_deck` frames the whole talk: the section cards, the three takeaways and Ben's sign-off.
"""

from __future__ import annotations

import asyncio
import json
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from app.core.llm import (
    OPENAI_STRONG,
    Effort,
    NoModelKey,
    claude_reply,
    first_that_answers,
    json_object,
    openai_reply,
)
from app.core.settings import Settings
from app.features.media_production.errors import AvUnavailable

# The script's second reader: an OpenAI model other than the writer's, so it does not mark its own words.
_ATTEMPTS = 3
_MAX_SECTIONS = 4
# Slides narrated (and read) at once: a deck's whole script in about the time of its slowest slide.
NARRATION_WORKERS = 16
# About eleven minutes of Ben at his pace, less the cards, countdowns and pauses between slides.
_TALK_WORDS = 1450
_INTRO_WORDS = 27
_ITEM_WORDS = (12, 30)
# An ElevenLabs audio tag such as [chuckles]: voiced, never read out or captioned.
AUDIO_TAG = re.compile(r"\[[^\]]*\]")
# A filler said before anything else. Every line is written without sight of its neighbours, so
# the same opener would otherwise start one line after another.
_OPENING_FILLER = re.compile(
    r"^(?:right|okay|ok|alright|all right|so|now|well)\s*(?:,|\.{3}|…|\.|!)\s*", re.I
)

_SYSTEM_PROMPT = (
    "You write what Ben says in a medical teaching video, one slide at a time. Ben is an experienced UK GP "
    "giving a relaxed talk to colleagues: calm, warm, dryly funny, never reading from a script. "
    "He never says his own name: another presenter may voice his words. You reply with JSON only."
)

_PROMPT = """\
Slide {number} of {total}. Title: {title}

The slide shows these {count} items one at a time, in this order (a main point, then its sub-points):
{items}

Ben's notes for this slide (the source of truth for the facts; never contradict or go beyond them):
{notes}

Write what Ben says as JSON: {{"intro": "...", "items": ["...", ...], "callouts": [null, ...]}}

How Ben talks:
- Like a good presenter who knows the material and is thinking aloud, not reciting. Short sentences mixed
  with longer ones. He pauses: use "..." for a beat. He never uses a dash.
- He talks TO the listener: "you'll have seen this", "so what do we do?", an occasional rhetorical question.
- Now and then (not on every slide, and at most once per slide) something human: a dry aside, a gentle joke,
  a "we've all been there on a Friday afternoon" moment, or a nod to a guideline or everyday practice. Never
  forced, never at a patient's expense, and never a fact that is not in the notes.
- Occasional natural fillers ("now", "so", "honestly") in the middle of a line, never as its first word:
  each line is written on its own and they are played back to back, so an opener like "Right," or
  "Okay," would be heard again and again. Sparingly, one audio tag in square
  brackets where it fits, such as [chuckles], [sighs] or [thoughtful]. At most one tag per slide.
- Spoken English: spell out numbers, units and abbreviations as a person says them ("one hundred and forty
  over ninety", "twice a day"). No bullet characters, no markdown, and never read the slide text out verbatim.

What goes where (this keeps his words in step with the slide, so it is strict):
- "intro" is said while only the title is showing: one or two sentences that set the slide up or link from
  the last one, in at most {intro_words} words. It must not state or preview any item. If there are no
  items, "intro" is everything he says on this slide (two to four sentences), faithful to the notes; if
  the notes pose a question to the listener, he asks it and stops.
- "items" has exactly {count} strings. Item N is said the moment item N appears and is about that item only:
  the one thing worth knowing about it (the why, or the clinical detail), in a single sentence of about
  {item_words} words. Never mention a later item, never repeat an earlier one, never say "next" or
  "moving on".
- The whole talk has to finish in ten to twelve minutes, so the word counts above are a budget, not a
  suggestion: no item goes more than a few words over. The humour stays; it is one line on this slide
  that lands in passing and may take up to fifteen extra words, never an added sentence on every item.
- "callouts" has exactly {count} entries, one per item. An entry is null unless that item's text on the
  slide states a clinical number worth remembering (a threshold, score, dose or duration, never the
  patient's own age or details); then it is
  {{"value": "...", "label": "..."}}: "value" is the number exactly as the slide writes it, with its sign
  or unit, in at most 12 characters ("-2.5", "70 mg", "over 65"), and "label" says what it is in at most
  four words. Never a number that is not in the item's own text.
"""

_QUESTION_RULE = """
This slide shows only the question. Ben asks it in at most twenty words, without hinting at the answer,
and his last words are the question itself. A silent three-second countdown follows on screen, so he
does not answer it, does not say how long the pause is and says nothing after the question.
"""

_PLAN_PROMPT = """\
The talk is "{title}". Its slides, in order:
{outline}

Plan how the talk is framed, as JSON:
{{"sections": [{{"before": 2, "title": "...", "line": "..."}}], "recap_intro": "...",
  "takeaways": [{{"text": "...", "line": "..."}}, {{"text": "...", "line": "..."}},
  {{"text": "...", "line": "..."}}], "signoff": "..."}}

- "sections": split the talk into {parts} parts. "before" is the number of the slide a part starts with;
  a title card is shown just before that slide. The first part starts at slide 2 or later. A part never
  starts at the slide straight after one marked (question), because that slide is the answer. "title" is
  at most four words. "line" is the one short sentence Ben says over the card to move the talk on.
- "recap_intro": one sentence Ben says as the recap slide opens, before the first takeaway.
- "takeaways": exactly three things worth remembering, the most useful in practice, taken only from the
  slides above. "text" is what the recap slide shows: at most twelve words, no full stop. "line" is what
  Ben says as it appears: one sentence. Neither may contain a figure, statistic, guideline or
  claim that is not written in the slides above; if the slides say "reduce", he does not say "halve".
- "signoff": Ben's goodbye over the closing card, one or two warm sentences. He thanks the listener and
  wishes them well. He names no company, podcast or series.
- Everything Ben says is spoken English in the voice described above: numbers and abbreviations as a
  person says them, no markdown, no new facts. No line opens with a filler such as "Right," or "Okay,".
"""


def slide_items(slide: dict[str, Any]) -> list[str]:
    """The slide's bullets flattened in reveal order: each main bullet, then its sub-bullets."""
    items: list[str] = []
    for bullet in slide.get("bullets") or []:
        if isinstance(bullet, dict):
            items.append(str(bullet.get("text", "")))
            for sub in bullet.get("sub_bullets") or []:
                items.append(str(sub.get("text", "")) if isinstance(sub, dict) else str(sub))
        else:
            items.append(str(bullet))
    return items


# One reply is a slide's lines or a whole deck read through: minutes, never the SDKs' default of ten
# minutes tried three times, which held an agent run half an hour on one stalled connection.
_REPLY_SECONDS = 240
# Claude 5.5 thinks by default and the thinking counts in max_tokens: a cut-off reply raises and
# would silently fall to OpenAI, so every caller gets headroom and low effort unless it says otherwise.
_CLAUDE_MAX_TOKENS = 16_000


def complete(
    settings: Settings,
    prompt: str,
    *,
    system: str = _SYSTEM_PROMPT,
    openai_model: str = OPENAI_STRONG,
    claude_first: bool = False,
    claude_max_tokens: int = _CLAUDE_MAX_TOKENS,
    claude_effort: Effort | None = "low",
    claude_seconds: float = _REPLY_SECONDS,
) -> str:
    """One model reply, from `openai_model` (gpt-6.1-sol unless told otherwise).

    Claude answers if it is unavailable. Blocking: every caller runs in a worker thread, so the
    shared async helpers run on a loop of their own.

    `claude_first` turns the order round, for a second reader that should not be the model
    that wrote the words it is reading.
    """

    async def from_openai(api_key: str) -> str:
        """The reply from `openai_model`."""
        return await openai_reply(
            api_key,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            model=openai_model,
            timeout=_REPLY_SECONDS,
        )

    async def from_claude(api_key: str) -> str:
        """The reply from Claude."""
        return await claude_reply(
            api_key,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=claude_max_tokens,
            timeout=claude_seconds,
            effort=claude_effort,
        )

    attempts = [
        ("openai", settings.openai_api_key, from_openai),
        ("claude", settings.anthropic_api_key, from_claude),
    ]
    if claude_first:
        attempts.reverse()
    # A loop of its own that is never made the thread's current one, so this leaves no mark on a caller's.
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(first_that_answers(attempts))
    except NoModelKey as exc:
        raise AvUnavailable("No language model is configured on this environment") from exc
    finally:
        loop.close()


def _said(value: object) -> str:
    """A string as written by the model with its dashes turned into commas and any opening filler
    ("Right, ...") dropped, or "" for anything else."""
    if not isinstance(value, str):
        return ""
    said = _OPENING_FILLER.sub("", re.sub(r"\s*[—–]\s*", ", ", value).strip())
    return said[:1].upper() + said[1:]


def item_words(slides: list[dict[str, Any]], talk: int = _TALK_WORDS) -> int:
    """How many words Ben gets per bullet so that the whole deck runs for about eleven minutes.

    `talk` is the words to aim the whole talk at: fewer than usual, with a shorter shortest line,
    when a first writing ran over.
    """
    items = sum(len(slide_items(slide)) for slide in slides)
    shortest = _ITEM_WORDS[0] * talk // _TALK_WORDS
    return max(shortest, min(_ITEM_WORDS[1], (talk - _INTRO_WORDS * len(slides)) // max(1, items)))


def plain_speech(line: str) -> str:
    """A line as it is heard: without the audio tags that only the voice reads."""
    return " ".join(AUDIO_TAG.sub(" ", line).split())


def spoken_notes(narration: dict[str, Any]) -> str:
    """Ben's words for one slide as its speaker notes: the intro, then a line per bullet, without
    the audio tags that only the voice needs."""
    lines = [narration["intro"], *narration["items"]]
    return "\n\n".join(plain_speech(line) for line in lines)


def _callout(entry: object, shown: str) -> dict[str, str] | None:
    """A key number for the slide item `shown`, kept only if its digits really are in that item."""
    if not isinstance(entry, dict):
        return None
    value, label = _said(entry.get("value")), _said(entry.get("label"))
    digits = re.findall(r"\d+", value)
    if not label or not digits or len(value) > 14 or len(label) > 40:
        return None
    if not all(re.search(rf"(?<!\d){run}(?!\d)", shown) for run in digits):
        return None
    return {"value": value, "label": label}


def _parse(reply: str, shown: list[str]) -> dict[str, Any] | None:
    """The narration JSON if it has an intro and one non-empty line per item in `shown`, else None."""
    parsed = json_object(reply)
    if parsed is None:
        return None
    intro, items = _said(parsed.get("intro")), parsed.get("items")
    if not intro or not isinstance(items, list) or len(items) != len(shown):
        return None
    if not all(_said(item) for item in items):
        return None
    callouts = parsed.get("callouts")
    if not isinstance(callouts, list) or len(callouts) != len(shown):
        callouts = [None] * len(shown)
    return {
        "intro": intro,
        "items": [_said(item) for item in items],
        "callouts": [_callout(entry, text) for entry, text in zip(callouts, shown, strict=True)],
    }


def narrate_slide(
    settings: Settings, slide: dict[str, Any], total: int = 0, words: int = _ITEM_WORDS[1]
) -> dict[str, Any]:
    """Returns `{"intro", "items", "callouts"}` for a slide, reusing a stored narration that still fits.

    A slide with no bullets gets no items: its whole narration is the intro. `callouts` holds,
    per item, the key number to show large beside it, or None. `words` is the length of an item's line.
    """
    items = slide_items(slide)
    stored = slide.get("narration")
    if isinstance(stored, dict):
        kept = _parse(json.dumps(stored), items)
        if kept:
            return kept
    prompt = _PROMPT.format(
        number=slide.get("position", "?"),
        total=total or "?",
        title=slide.get("title", ""),
        count=len(items),
        items="\n".join(f"{number}. {text}" for number, text in enumerate(items, 1))
        or "(no list on this slide)",
        notes=slide.get("source_notes") or slide.get("speaker_notes", ""),
        intro_words=_INTRO_WORDS - 5,
        item_words=words,
    )
    if is_question(slide):
        prompt += _QUESTION_RULE
    for _ in range(_ATTEMPTS):
        narration = _parse(complete(settings, prompt), items)
        if narration:
            return narration
    raise AvUnavailable(f"Could not write a narration with {len(items)} items for '{slide.get('title')}'")


def is_question(slide: dict[str, Any]) -> bool:
    """Whether a slide only poses a question to the listener: a title ending in "?" and nothing under it."""
    return (
        not slide_items(slide)
        and not str(slide.get("explanation") or "").strip()
        and str(slide.get("title") or "").strip().endswith("?")
    )


def _parse_plan(reply: str, slides: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The deck plan if it has three takeaways, a recap line and a sign-off, with its usable sections."""
    parsed = json_object(reply)
    if parsed is None:
        return None
    takeaways = parsed.get("takeaways")
    if not isinstance(takeaways, list) or len(takeaways) != 3:
        return None
    kept = [
        {"text": _said(entry.get("text")).rstrip("."), "line": _said(entry.get("line"))}
        for entry in takeaways
        if isinstance(entry, dict)
    ]
    recap_intro, signoff = _said(parsed.get("recap_intro")), _said(parsed.get("signoff"))
    if len(kept) != 3 or not all(entry["text"] and entry["line"] for entry in kept):
        return None
    if not recap_intro or not signoff:
        return None
    sections: dict[int, dict[str, Any]] = {}
    proposed = parsed.get("sections")
    for entry in proposed if isinstance(proposed, list) else []:
        if not isinstance(entry, dict):
            continue
        before, title, line = entry.get("before"), _said(entry.get("title")), _said(entry.get("line"))
        if not isinstance(before, int) or not 2 <= before <= len(slides) or not title or not line:
            continue
        if is_question(slides[before - 2]):
            continue  # a card here would come between a question and its answer
        sections.setdefault(before, {"before": before, "title": title, "line": line})
    return {
        "sections": [sections[before] for before in sorted(sections)][:_MAX_SECTIONS],
        "recap_intro": recap_intro,
        "takeaways": kept,
        "signoff": signoff,
    }


def plan_deck(settings: Settings, content: dict[str, Any]) -> dict[str, Any]:
    """How the talk is framed: `sections` (a title card before a slide, with Ben's line),
    `recap_intro`, three `takeaways` and Ben's `signoff`. A stored plan that still fits is reused.
    """
    slides = [slide for slide in content.get("slides") or [] if isinstance(slide, dict)]
    stored = content.get("presentation")
    if isinstance(stored, dict):
        kept = _parse_plan(json.dumps(stored), slides)
        if kept:
            return kept
    outline = []
    for number, slide in enumerate(slides, 1):
        shown = "; ".join(slide_items(slide)) or str(slide.get("explanation") or "")
        mark = " (question)" if is_question(slide) else ""
        outline.append(f"{number}. {slide.get('title', '')}{mark}: {shown[:400]}")
    count = len(slides)
    parts = "three or four" if count >= 12 else "two or three" if count >= 6 else "no (an empty list of)"
    prompt = _PLAN_PROMPT.format(title=content.get("title", ""), outline="\n".join(outline), parts=parts)
    for _ in range(_ATTEMPTS):
        plan = _parse_plan(complete(settings, prompt), slides)
        if plan:
            return plan
    raise AvUnavailable(f"Could not plan the talk '{content.get('title')}'")


def keeps_stored_narration(slide: dict[str, Any]) -> bool:
    """Whether `narrate_slide` would reuse this slide's stored narration instead of writing a new one."""
    stored = slide.get("narration")
    return isinstance(stored, dict) and _parse(json.dumps(stored), slide_items(slide)) is not None


def narrate_deck(settings: Settings, payload: dict[str, Any], talk: int = _TALK_WORDS) -> None:
    """Writes onto `payload` what Ben says: the talk's framing, and a narration on every slide, aimed
    at `talk` words in all.

    The notes a slide was written from stay as the source of its facts (`source_notes`); the
    notes shown with the slide become what Ben actually says.
    """
    slides = payload["slides"]
    with ThreadPoolExecutor(NARRATION_WORKERS) as pool:
        plan = pool.submit(plan_deck, settings, payload)
        words = item_words(slides, talk)
        narrations = list(pool.map(lambda slide: narrate_slide(settings, slide, len(slides), words), slides))
        payload["presentation"] = plan.result()
    for slide, narration in zip(slides, narrations, strict=True):
        slide["narration"] = narration
        slide.setdefault("source_notes", slide.get("speaker_notes", ""))
        slide["speaker_notes"] = spoken_notes(narration)
