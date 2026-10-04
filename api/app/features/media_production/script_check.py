"""Reads what was written to be spoken against what it was written from, before any of it is voiced.

The narration of a slide, and a podcast's dialogue, are each written by a model that sees one
slide or one summary and is free with it: a name from nowhere, "or" where the source says "and",
a cause the source never gave. Voicing is the step that costs money, so the words are read
first: a rule pass for what a rule can see, then a second model that did not write them. A line
this run wrote is corrected and read again; a line somebody edited by hand is only reported,
because the person who typed it outranks the reader.

The result is the `script` half of an item's `review`: the exact lines that were read (so the
voicing routes can refuse anything else), what is still flagged, and every change made.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any

from app.core.settings import Settings
from app.features.media_production.errors import AvUnavailable
from app.features.media_production.podcast_script import generate_script, split_script
from app.features.media_production.slide_narration import (
    _TALK_WORDS,
    NARRATION_WORKERS,
    json_object,
    keeps_stored_narration,
    narrate_deck,
    slide_items,
    spoken_notes,
)
from app.features.media_production.summary_text import format_summary_for_podcast

# A model call: the prompt in, the reply out. Passed in so a test can script the reader.
Complete = Callable[[str], str]

CHECK_SYSTEM = (
    "You are a careful medical editor checking a script against its source before it is recorded. "
    "You report only real departures from the source, never style. You reply with JSON only."
)
ISSUE_KINDS = ("name", "number", "logic", "unsourced", "story", "rule", "length")
# How many times a corrected line is read again before what is left is handed to a person.
ROUNDS = 2
_CONTEXT_CHARACTERS = 14000
# Below this there is nothing to be faithful to, and every line would be reported as unsourced.
_THIN_SOURCE_CHARACTERS = 200
_LENGTH_ALLOWANCE = 1.1

_AUDIO_TAG = re.compile(r"\[[^\]]*\]")
_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")
_OPENER = re.compile(r"^(?:right|okay|ok|alright|all right|so|now|well)\b", re.I)
_VIDEO = re.compile(r"\bvideo\s+(?:consultation|consult|call|appointment)", re.I)
_CALENDAR = frozenset(
    [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
        "christmas",
        "easter",
    ]
)

_PROMPT = """\
These lines are about to be recorded for a medical teaching {what}. They were written from the
source below and must be faithful to it.

Source for these lines (the only facts they may state):
{source}

The rest of the material, for names and the story only:
{context}

The lines, numbered:
{lines}

A rule-based pass spotted these possible problems (confirm or dismiss each):
{hints}

Report every line that has one of these faults:
- name: a name, age, job or other detail of a person that differs from the material.
- number: a figure, dose, threshold or duration that differs from the source, or one the source
  does not give.
- logic: the meaning of a rule changed, such as "or" for "and", "at least" for "more than", or the
  steps in a different order.
- unsourced: a clinical claim, comparison or cause that the source does not state.
- story: the patient's story told wrongly (who did what, where a reading was taken, what was
  asked for).
- rule: a remote appointment called a video consultation when the material does not say video, or
  a line that opens with a filler such as "So" or "Now".

Do not report style, humour, asides, rhetorical questions, or a number merely spelled out in
words. A faithful line is not reported.

Reply as JSON: {{"issues": [{{"line": 3, "kind": "number", "quote": "the words at fault",
"why": "one sentence", "fix": "the whole line rewritten"}}]}}
"fix" is the complete corrected line in the same voice and at about the same length, changing as
little as possible, keeping any audio tag in square brackets such as [chuckles], with numbers
spoken as words. An empty list if nothing is wrong.
"""

_NO_SOURCE = (
    "No source material was given. Do not report number or unsourced faults: check only that the "
    "lines agree with one another, and the rule faults."
)


def _plain(line: str) -> str:
    """A line as it is heard: without the audio tags that only the voice reads."""
    return " ".join(_AUDIO_TAG.sub(" ", line).split())


def slide_source(slide: dict[str, Any]) -> str:
    """What a slide's narration was written from: its title, what it shows, and its notes."""
    notes = str(slide.get("source_notes") or slide.get("speaker_notes") or "")
    shown = "\n".join(f"- {item}" for item in slide_items(slide))
    explanation = str(slide.get("explanation") or "")
    return "\n".join(part for part in (str(slide.get("title") or ""), shown, explanation, notes) if part)


def source_hash(slide: dict[str, Any]) -> str:
    """A fingerprint of what a slide's narration was written from, to notice when that has changed."""
    return hashlib.sha256(slide_source(slide).encode()).hexdigest()[:16]


def _slides(content: dict[str, Any]) -> list[dict[str, Any]]:
    """The deck's slides, ignoring anything that is not one."""
    slides = content.get("slides")
    return [slide for slide in slides if isinstance(slide, dict)] if isinstance(slides, list) else []


def _narration_lines(slide: dict[str, Any]) -> list[str]:
    """What is said on one slide, in order: the intro, then a line per item; empty if not yet written."""
    narration = slide.get("narration")
    if not isinstance(narration, dict) or not isinstance(narration.get("items"), list):
        return []
    return [str(narration.get("intro") or ""), *(str(item) for item in narration["items"])]


def _framing_lines(plan: object) -> list[str]:
    """What is said around the slides, in order: each section card's line, the recap's opening,
    a line per takeaway, and the sign-off; empty if the talk has not been planned."""
    if not isinstance(plan, dict):
        return []
    sections = [entry for entry in plan.get("sections") or [] if isinstance(entry, dict)]
    takeaways = [entry for entry in plan.get("takeaways") or [] if isinstance(entry, dict)]
    return [
        *(str(entry.get("line") or "") for entry in sections),
        str(plan.get("recap_intro") or ""),
        *(str(entry.get("line") or "") for entry in takeaways),
        str(plan.get("signoff") or ""),
    ]


def spoken_lines(kind: str, content: dict[str, Any]) -> list[str]:
    """Every line that voicing this item would speak, in order; empty when a part is still unwritten.

    A deck is its slides' narrations and then its framing. A summary or a podcast is its
    script, a turn per line.
    """
    if kind != "slide_deck":
        script = content.get("script")
        turns = split_script(script) if isinstance(script, str) else []
        return [f"{speaker}: {line}" for speaker, line in turns]
    per_slide = [_narration_lines(slide) for slide in _slides(content)]
    framing = _framing_lines(content.get("presentation"))
    if not per_slide or not framing or not all(per_slide):
        return []
    return [line for lines in per_slide for line in lines] + framing


def is_checked(kind: str, content: dict[str, Any]) -> bool:
    """Whether the lines voicing would speak are exactly the lines that were last checked."""
    review = content.get("review")
    script = review.get("script") if isinstance(review, dict) else None
    checked = script.get("lines") if isinstance(script, dict) else None
    spoken = spoken_lines(kind, content)
    return bool(spoken) and checked == spoken


def rule_hints(lines: list[str], source: str, whole: str) -> list[dict[str, Any]]:
    """What a rule can see wrong with `lines` (numbered from 1), as issues with no fix.

    `source` is what these lines were written from, and `whole` is all the material: a name is
    only strange if it appears nowhere in it.
    """
    known = set(re.findall(r"[a-z]+", whole.lower()))
    numbers = set(re.findall(r"\d+", source))
    hints: list[dict[str, Any]] = []

    def hint(number: int, kind: str, quote: str, why: str) -> None:
        """Records one possible problem on line `number`."""
        hints.append({"line": number, "kind": kind, "quote": quote, "why": why, "fix": ""})

    for number, line in enumerate(lines, 1):
        heard = _plain(line)
        for sentence in _SENTENCE_END.split(heard):
            for word in re.findall(r"[A-Za-z']+", sentence)[1:]:
                name = word.removesuffix("'s")
                if re.fullmatch(r"[A-Z][a-z]{2,}", name) and name.lower() not in known | _CALENDAR:
                    hint(number, "name", name, f"'{name}' appears nowhere in the material")
        for digits in re.findall(r"\d+", heard):
            if digits not in numbers:
                hint(number, "number", digits, f"{digits} is not in what this line was written from")
        video = _VIDEO.search(heard)
        if video and "video" not in whole.lower():
            hint(number, "rule", video.group(0), "The material does not describe a video consultation")
        opener = _OPENER.match(heard)
        if opener:
            hint(number, "rule", opener.group(0), "Opens with a filler")
    return hints


def _issues(
    complete: Complete, what: str, source: str, context: str, lines: list[str]
) -> list[dict[str, Any]]:
    """What the second reader finds wrong with `lines`; the rule pass's findings if it does not answer."""
    hints = rule_hints(lines, source, f"{source}\n{context}")
    thin = len(source.strip()) < _THIN_SOURCE_CHARACTERS
    prompt = _PROMPT.format(
        what=what,
        source=_NO_SOURCE if thin else source,
        context=context[:_CONTEXT_CHARACTERS] or "(none)",
        lines="\n".join(f"{number}. {line}" for number, line in enumerate(lines, 1)),
        hints="\n".join(f"- line {hint['line']}: {hint['why']}" for hint in hints) or "(none)",
    )
    parsed = json_object(complete(prompt))
    found = parsed.get("issues") if parsed is not None else None
    if not isinstance(found, list):
        return hints
    issues: list[dict[str, Any]] = []
    for entry in found:
        if not isinstance(entry, dict):
            continue
        number, kind = entry.get("line"), entry.get("kind")
        if not isinstance(number, int) or not 1 <= number <= len(lines):
            continue
        issues.append(
            {
                "line": number,
                "kind": kind if kind in ISSUE_KINDS else "unsourced",
                "quote": str(entry.get("quote") or "")[:200],
                "why": str(entry.get("why") or "")[:400],
                "fix": str(entry.get("fix") or "").strip(),
            }
        )
    return issues


def _fixed(before: str, fix: str) -> str:
    """A proposed line made safe to use: on one line, with any audio tag of the original kept."""
    after = " ".join(fix.split())
    missing = [tag for tag in _AUDIO_TAG.findall(before) if tag not in after]
    return " ".join([*missing, after]) if after else before


def read_lines(
    complete: Complete, *, what: str, source: str, context: str, lines: list[str], fixable: bool
) -> tuple[list[str], list[dict[str, Any]], list[dict[str, Any]]]:
    """Reads `lines` against `source`, correcting them when `fixable`.

    Returns the lines as they now stand, what is still flagged, and each change made (`line`,
    `before`, `after`, `kind`, `why`). A corrected line is read again, `ROUNDS` times at most.
    """
    lines = list(lines)
    changes: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    for attempt in range(ROUNDS + 1):
        issues = _issues(complete, what, source, context, lines)
        if not fixable or attempt == ROUNDS:
            break
        changed = False
        for issue in issues:
            before = lines[issue["line"] - 1]
            after = _fixed(before, issue["fix"])
            if after == before:
                continue
            lines[issue["line"] - 1] = after
            changes.append(
                {
                    "line": issue["line"],
                    "before": before,
                    "after": after,
                    "kind": issue["kind"],
                    "why": issue["why"],
                }
            )
            changed = True
        if not changed:
            break
    return lines, issues, changes


def _placed(entries: list[dict[str, Any]], part: str, slide: int | None) -> list[dict[str, Any]]:
    """Issues or changes with where they are: which `part` of the item, and which slide of a deck."""
    return [{"part": part, "slide": slide, **entry} for entry in entries]


def _set_framing(plan: dict[str, Any], lines: list[str]) -> None:
    """Writes `lines` back onto the talk's framing, in the order `_framing_lines` read them."""
    rest = iter(lines)
    for entry in plan.get("sections") or []:
        if isinstance(entry, dict):
            entry["line"] = next(rest)
    plan["recap_intro"] = next(rest)
    for entry in plan.get("takeaways") or []:
        if isinstance(entry, dict):
            entry["line"] = next(rest)
    plan["signoff"] = next(rest)


def _review(
    kind: str, content: dict[str, Any], issues: list[dict[str, Any]], changes: list[dict[str, Any]]
) -> None:
    """Records on `content` what was read, what is still flagged and what was changed."""
    review = dict(content.get("review") or {})
    review.pop("error", None)
    review["script"] = {
        "checked_at": datetime.now(UTC).isoformat(),
        "lines": spoken_lines(kind, content),
        "sources": {str(number): source_hash(slide) for number, slide in enumerate(_slides(content), 1)},
        "issues": issues,
        "changes": changes,
    }
    content["review"] = review


def check_deck(
    complete: Complete, content: dict[str, Any], *, written: frozenset[int], plan_written: bool
) -> dict[str, Any]:
    """Reads a narrated deck, returning its content with the corrections and the review on it.

    `written` holds the slides (numbered from 1) whose narration this run wrote, and
    `plan_written` says the same of the framing: only those are corrected, the rest reported.
    """
    content = {**content, "slides": [dict(slide) for slide in _slides(content)]}
    slides: list[dict[str, Any]] = content["slides"]
    whole = "\n\n".join(slide_source(slide) for slide in slides)

    def read(number: int) -> tuple[list[str], list[dict[str, Any]], list[dict[str, Any]]]:
        """Reads one slide's lines against that slide."""
        slide = slides[number - 1]
        return read_lines(
            complete,
            what="video",
            source=slide_source(slide),
            context=whole,
            lines=_narration_lines(slide),
            fixable=number in written,
        )

    with ThreadPoolExecutor(NARRATION_WORKERS) as pool:
        framing = pool.submit(
            read_lines,
            complete,
            what="video",
            source=whole,
            context="",
            lines=_framing_lines(content.get("presentation")),
            fixable=plan_written,
        )
        results = list(pool.map(read, range(1, len(slides) + 1)))
        framing_lines, framing_issues, framing_changes = framing.result()

    issues: list[dict[str, Any]] = []
    changes: list[dict[str, Any]] = []
    for number, (lines, found, made) in enumerate(results, 1):
        slide = slides[number - 1]
        if made:
            slide["narration"] = {**slide["narration"], "intro": lines[0], "items": lines[1:]}
            slide["speaker_notes"] = spoken_notes(slide["narration"])
        issues += _placed(found, "slide", number)
        changes += _placed(made, "slide", number)
    if framing_changes:
        content["presentation"] = json.loads(json.dumps(content["presentation"]))
        _set_framing(content["presentation"], framing_lines)
    issues += _placed(framing_issues, "framing", None)
    changes += _placed(framing_changes, "framing", None)

    words = sum(len(_plain(line).split()) for line in spoken_lines("slide_deck", content))
    if words > _TALK_WORDS * _LENGTH_ALLOWANCE:
        why = f"The talk is about {words} words; twelve minutes is about {_TALK_WORDS}"
        issues.append(
            {"part": "deck", "slide": None, "line": 0, "kind": "length", "quote": "", "why": why, "fix": ""}
        )
    _review("slide_deck", content, issues, changes)
    return content


def prepare_deck(
    settings: Settings, content: dict[str, Any], *, rewrite: bool, complete: Complete
) -> dict[str, Any]:
    """Writes whatever of a deck's narration is missing or out of date, then reads all of it.

    A slide is narrated afresh when it has no narration, when what it was written from has
    changed since the last check, or when `rewrite` asks for everything again. The framing is
    planned afresh whenever any slide is. Nothing here is voiced.
    """
    slides = [dict(slide) for slide in _slides(content)]
    if not slides or len(slides) != len(content.get("slides") or []):
        raise AvUnavailable("This deck has no slides to narrate")
    payload = {**content, "slides": slides}
    stored = (payload.get("review") or {}).get("script") or {}
    checked = stored.get("sources") if isinstance(stored, dict) else None
    sources: dict[str, Any] = checked if isinstance(checked, dict) else {}

    written: set[int] = set()
    for number, slide in enumerate(slides, 1):
        moved = sources.get(str(number)) not in (None, source_hash(slide))
        if rewrite or moved or not keeps_stored_narration(slide):
            slide.pop("narration", None)
            written.add(number)
    plan_written = bool(written) or not _framing_lines(payload.get("presentation"))
    if plan_written:
        payload.pop("presentation", None)

    narrate_deck(settings, payload)
    return check_deck(complete, payload, written=frozenset(written), plan_written=plan_written)


def prepare_podcast(
    settings: Settings, *, kind: str, title: str, content: dict[str, Any], rewrite: bool, complete: Complete
) -> dict[str, Any]:
    """Writes a summary's or an episode's script if it has none (or `rewrite` asks), then reads it.

    A summary's script is read against the summary; an episode's against its `body_md`. A
    script this run wrote is corrected; one already there is only reported on.
    """
    if kind == "summary":
        source = format_summary_for_podcast(title, content)
    else:
        source = str(content.get("body_md") or "")
    script = content.get("script")
    written = rewrite or not isinstance(script, str) or not split_script(script)
    if written:
        script = generate_script(settings, source or title)
    turns = split_script(str(script))
    if not turns:
        raise AvUnavailable("Script did not contain Ben/Michelle dialogue")
    lines, issues, changes = read_lines(
        complete,
        what="podcast",
        source=source,
        context="",
        lines=[line for _speaker, line in turns],
        fixable=written,
    )
    if written or changes:
        script = "\n\n".join(f"{speaker}: {line}" for (speaker, _old), line in zip(turns, lines, strict=True))
    content = {**content, "script": script}
    _review(kind, content, _placed(issues, "script", None), _placed(changes, "script", None))
    return content
