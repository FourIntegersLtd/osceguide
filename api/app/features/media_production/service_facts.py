"""Checks the clinical claims in teaching material against the guidelines: a deck, a summary or a
podcast here, and a platform station for `stations`.

Every claim that can be looked up (a threshold, a dose, a criterion, a target, a timing) is put
to Clinical Buddy's guideline library and to its clinical web search at once, and what each said
is kept, labelled by source, so the reader can weigh one against the other. Nothing here changes
the material: a contradiction
comes back as a suggested replacement, with the passage and page it rests on, for a person to
accept or dismiss.

The result is the `facts` half of an item's `review`, which only platform admins are served.
Each caller cuts its material into sections, and says where each sits; that is merged into every
claim found in it, so the screen can say "Slide 3" or "Examiner notes".
"""

from __future__ import annotations

import asyncio
import hashlib
import re
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from app.core.logging import get_logger
from app.core.ports import GuidelineIndex, GuidelinePassage, GuidelineWeb, WebAnswer
from app.core.settings import get_settings
from app.features.media_production.errors import ClaimOutsideItem

# Re-exported: a caller in another slice hands in its own checking model as one.
from app.features.media_production.script_check import Complete as Complete
from app.features.media_production.script_check import slide_source
from app.features.media_production.slide_narration import complete as model_reply
from app.features.media_production.slide_narration import json_object
from app.features.media_production.summary_text import format_summary_for_podcast
from app.features.tutor_memory import service_search as tutor_search

log = get_logger(__name__)

# Where a stretch of material sits (merged into each claim found in it), and its text.
Section = tuple[dict[str, Any], str]
# Handed the claims judged so far, each time one more settles, so a screen can fill in as it runs.
Progress = Callable[[dict[str, Any]], Awaitable[None]]

FACT_SYSTEM = (
    "You are a careful UK clinical editor checking teaching material against guidelines. "
    "You never rely on your own memory of a guideline: only on the passages you are shown. "
    "You reply with JSON only."
)
MAX_CLAIMS = 60
PASSAGES_PER_CLAIM = 5
# Each claim waits about 30 s on the clinical web, so this is what bounds a check's length. Clinical
# Buddy's web search answered 24 at once with none refused (measured 2026-10-04).
CLAIMS_AT_ONCE = 24
VERDICTS = ("supported", "contradicted", "not_found")
_QUOTE_CHARACTERS = 400
_SECTION_CHARACTERS = 6000

_CLAIMS_PROMPT = """\
This is teaching material for UK doctors, "{title}", in numbered sections:

{sections}

List the clinical claims in it that a guideline could confirm or contradict: thresholds, doses,
diagnostic criteria, targets, timings, drug choices, referral and safety rules. Leave out the
patient's own story and details, teaching advice, and anything that is opinion. One entry per
distinct claim, the most consequential first, at most {limit}.

Reply as JSON: {{"claims": [{{"section": 3, "claim": "the claim in one sentence, as the material
states it", "question": "the question to put to a guideline search to check it"}}]}}
{earlier}"""

_EARLIER_CLAIMS = """
An earlier version of this text was checked with these claims. Where the text still makes one of
them, give it word for word as listed here; word only new or changed claims afresh:
{claims}
"""

_JUDGE_PROMPT = """\
A claim in teaching material for UK doctors:
{claim}

The text it appears in, line by line:
{text}

{evidence_heading}
{evidence}

Decide on the evidence shown only:
- "supported": the evidence states the same thing, with the same numbers and conditions.
- "contradicted": the evidence states a different fact the claim cannot be true alongside: another
  number, drug, criterion or instruction.
- "not_found": the evidence does not settle it either way. Evidence that is silent on the claim, or
  that says a guideline does not mention it, is "not_found" and never "contradicted".

Reply as JSON: {{"verdict": "...", "evidence": 2, "quote": "the words of that piece of evidence
that decide it, copied exactly", "why": "one sentence", "line": 3, "new": "..."}}
"evidence" is the number of the piece that decides it, or null. Give "line" and "new" only when
contradicted: "line" is the number of the line above that says the wrong thing, and "new" is that
whole line rewritten so it is right, changing only what is wrong and keeping everything else it says
and the way it says it. Otherwise both are null.
"""


def sections_of(kind: str, title: str, content: dict[str, Any]) -> list[Section]:
    """A media item's text in the sections a claim is located by: a deck's slides, or the whole of
    a summary or a podcast as one."""
    if kind == "slide_deck":
        slides = content.get("slides")
        listed = [slide for slide in slides if isinstance(slide, dict)] if isinstance(slides, list) else []
        return [({"slide": number}, slide_source(slide)) for number, slide in enumerate(listed, 1)]
    if kind == "summary":
        return [({"slide": None}, format_summary_for_podcast(title, content))]
    parts = (str(content.get("body_md") or ""), str(content.get("script") or ""))
    return [({"slide": None}, "\n\n".join(part for part in parts if part.strip()))]


def _claims(reply: str, sections: list[str]) -> list[dict[str, Any]]:
    """The claims a model listed, each tied to a section that exists."""
    parsed = json_object(reply)
    listed = parsed.get("claims") if parsed is not None else None
    claims: list[dict[str, Any]] = []
    for entry in listed if isinstance(listed, list) else []:
        if not isinstance(entry, dict):
            continue
        section, claim = entry.get("section"), str(entry.get("claim") or "").strip()
        if not isinstance(section, int) or not 1 <= section <= len(sections) or not claim:
            continue
        claims.append(
            {"section": section, "claim": claim, "question": str(entry.get("question") or claim).strip()}
        )
    return claims[:MAX_CLAIMS]


_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")


def lines_of(text: str) -> list[str]:
    """A section's text as the lines the judge picks a wrong one from: each line, split at its
    sentences, without the bullet it was listed under. Each is exactly as written, so it can be
    swapped for its correction."""
    lines = (part.lstrip("-*• ").strip() for line in text.splitlines() for part in _SENTENCE_END.split(line))
    return [line for line in lines if line]


def _judgement(reply: str, pieces: int) -> dict[str, Any]:
    """A model's verdict on one claim, with anything malformed read as "not found"."""
    parsed = json_object(reply) or {}
    verdict = parsed.get("verdict")
    chosen = parsed.get("evidence")
    return {
        "verdict": verdict if verdict in VERDICTS else "not_found",
        "evidence": chosen if isinstance(chosen, int) and 1 <= chosen <= pieces else None,
        "quote": str(parsed.get("quote") or "")[:_QUOTE_CHARACTERS],
        "why": str(parsed.get("why") or "")[:400],
        "line": parsed.get("line") if isinstance(parsed.get("line"), int) else None,
        "new": str(parsed.get("new") or ""),
    }


def _passage_lines(passages: list[GuidelinePassage]) -> str:
    """Guideline passages numbered for the judge, each with where it comes from."""
    return "\n\n".join(
        f"[{number}] {passage.source}"
        + (f", {passage.section}" if passage.section else "")
        + (f", page {passage.page}" if passage.page is not None else "")
        + f":\n{passage.text}"
        for number, passage in enumerate(passages, 1)
    )


def _reference_lines(found: WebAnswer) -> str:
    """A web answer for the judge: the answer, then its references numbered as it cites them."""
    listed = "\n".join(
        f"[{number}] {reference.get('title') or reference.get('website_name') or ''} "
        f"({reference.get('url') or ''}): {' '.join(str(quote) for quote in reference.get('quotes') or [])}"
        for number, reference in enumerate(found.references, 1)
    )
    return f"{found.answer}\n\nReferences:\n{listed or '(none)'}"


async def _judge(
    complete: Complete, claim: dict[str, Any], text: str, heading: str, evidence: str, pieces: int
) -> dict[str, Any]:
    """One verdict on one claim from one kind of evidence."""
    numbered = "\n".join(f"Line {number}: {line}" for number, line in enumerate(lines_of(text), 1))
    prompt = _JUDGE_PROMPT.format(
        claim=claim["claim"], text=numbered[:_SECTION_CHARACTERS], evidence_heading=heading, evidence=evidence
    )
    return _judgement(await asyncio.to_thread(complete, prompt), pieces)


def _finding(kind: str, judged: dict[str, Any] | None, **source: Any) -> dict[str, Any]:
    """What one source said about a claim, labelled by where it came from.

    Clinical Buddy tags each source with a reliability and a type; both are empty where it did not.
    """
    return {
        "kind": kind,
        "verdict": judged["verdict"] if judged else "not_found",
        "why": judged["why"] if judged else "Nothing came back for this claim.",
        "source": "",
        "section": "",
        "page": None,
        "url": None,
        "quote": judged["quote"] if judged else "",
        "reliability": "",
        "source_type": "",
        **source,
    }


def _timed(kind: str, started: float, searched: float, *, found: bool) -> None:
    """Logs how long one source took to search and then to be judged, so the slow step is visible."""
    log.info(
        "fact check source timed",
        kind=kind,
        found=found,
        search_seconds=round(searched - started, 1),
        judge_seconds=round(time.monotonic() - searched, 1),
    )


async def _ask_library(
    claim: dict[str, Any], text: str, guidelines: GuidelineIndex, complete: Complete
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """The guideline library's verdict on a claim, and the passage it rests on."""
    started = time.monotonic()
    passages = await guidelines.search(query=claim["question"], limit=PASSAGES_PER_CLAIM, rerank=True)
    searched = time.monotonic()
    if not passages:
        _timed("guideline", started, searched, found=False)
        return None, _finding("guideline", None)
    judged = await _judge(
        complete,
        claim,
        text,
        "Passages from the guideline library, numbered:",
        _passage_lines(passages),
        len(passages),
    )
    _timed("guideline", started, searched, found=True)
    if judged["evidence"] is None or judged["verdict"] == "not_found":
        return judged, _finding("guideline", judged)
    passage = passages[judged["evidence"] - 1]
    return judged, _finding(
        "guideline",
        judged,
        source=passage.source,
        section=passage.section,
        page=passage.page,
        quote=judged["quote"] or passage.text[:_QUOTE_CHARACTERS],
        reliability=passage.reliability,
        source_type=passage.source_type,
    )


async def _ask_web(
    claim: dict[str, Any], text: str, web: GuidelineWeb, complete: Complete
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """The clinical web's verdict on a claim, and the page it rests on."""
    started = time.monotonic()
    found = await web.answer(question=claim["question"])
    searched = time.monotonic()
    if found is None:
        _timed("web", started, searched, found=False)
        return None, _finding("web", None)
    judged = await _judge(
        complete,
        claim,
        text,
        "What a search of the clinical web found:",
        _reference_lines(found),
        len(found.references),
    )
    _timed("web", started, searched, found=True)
    if judged["verdict"] == "not_found":
        return judged, _finding("web", judged)
    cited = found.references[judged["evidence"] - 1] if judged["evidence"] is not None else {}
    return judged, _finding(
        "web",
        judged,
        source=str(cited.get("title") or cited.get("website_name") or "Clinical web search"),
        url=cited.get("url"),
        quote=judged["quote"] or found.answer[:_QUOTE_CHARACTERS],
        reliability=str(cited.get("reliability") or ""),
        source_type=str(cited.get("source_type") or ""),
    )


async def _check_claim(
    claim: dict[str, Any],
    text: str,
    *,
    guidelines: GuidelineIndex | None,
    web: GuidelineWeb | None,
    complete: Complete,
) -> dict[str, Any]:
    """One claim's verdict, what each source said, and a suggested replacement if it is wrong.

    The library and the web are both asked, at once, so the reader sees each one's answer side by side.
    """
    asks = []
    if guidelines is not None:
        asks.append(_ask_library(claim, text, guidelines, complete))
    if web is not None:
        asks.append(_ask_web(claim, text, web, complete))
    answers = await asyncio.gather(*asks)
    checked = ["guidelines" if finding["kind"] == "guideline" else "web" for _, finding in answers]
    evidence = [finding for _, finding in answers]
    verdicts = [judged for judged, _ in answers if judged is not None]

    said = {judged["verdict"] for judged in verdicts}
    if not checked:
        verdict = "not_checked"
    elif {"supported", "contradicted"} <= said:
        verdict = "conflict"
    elif "contradicted" in said:
        verdict = "contradicted"
    elif "supported" in said:
        verdict = "supported"
    else:
        verdict = "not_found"

    wrong = next(
        (judged for judged in verdicts if judged["verdict"] == "contradicted" and judged["new"]), None
    )
    decisive = next((judged for judged in verdicts if judged["verdict"] == verdict), None) or wrong
    suggestion = None
    if wrong is not None:
        # The wrong line is picked by number rather than copied out, so it is always the text as
        # written and the reader can swap it; a number that is not a line leaves only advice.
        lines = lines_of(text)
        line = wrong["line"]
        suggestion = {
            "old": lines[line - 1] if line is not None and 1 <= line <= len(lines) else None,
            "new": wrong["new"],
        }
    return _stored_claim(
        claim["claim"],
        verdict=verdict,
        why=decisive["why"] if decisive else "",
        checked=checked,
        evidence=evidence,
        suggestion=suggestion,
    )


def _stored_claim(
    claim: str,
    *,
    verdict: str,
    why: str,
    checked: list[str],
    evidence: list[dict[str, Any]],
    suggestion: dict[str, Any] | None,
) -> dict[str, Any]:
    """A claim as a check stores it, whether the platform or a person checked it."""
    return {
        "claim": claim,
        "verdict": verdict,
        "why": why,
        "checked": checked,
        "evidence": evidence,
        "suggestion": suggestion,
    }


async def check_facts(
    *,
    title: str,
    sections: list[Section],
    guidelines: GuidelineIndex | None,
    web: GuidelineWeb | None,
    complete: Complete,
    on_progress: Progress | None = None,
    earlier: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """The `facts` review of some material: each clinical claim, its verdict, evidence and suggestion,
    with where its section sits.

    `earlier` is a previous check's claims of the same text: a claim found again in the same words is
    given its earlier verdict without asking the sources again, unless the wrong line it named has
    gone from its section.

    With neither the library nor the web to ask, every claim comes back "not_checked". While it runs,
    `on_progress` is handed the same review so far, with a `progress` count, once the claims are found
    and again as each one settles.
    """
    started = time.monotonic()
    texts = [text for _, text in sections]
    numbered = _numbered(sections)
    known = {_wording(str(claim.get("claim") or "")): claim for claim in earlier or []}
    listed = "\n".join(f"- {claim['claim']}" for claim in earlier or [] if claim.get("claim"))
    prompt = _CLAIMS_PROMPT.format(
        title=title,
        sections=numbered,
        limit=MAX_CLAIMS,
        earlier=_EARLIER_CLAIMS.format(claims=listed) if listed else "",
    )
    claims = _claims(await asyncio.to_thread(complete, prompt), texts) if numbered.strip() else []
    extracted = time.monotonic()
    gate = asyncio.Semaphore(CLAIMS_AT_ONCE)
    settled: dict[int, dict[str, Any]] = {}
    reporting = asyncio.Lock()

    async def report() -> None:
        """Hands on the claims settled so far, one report at a time; a failed report never stops the check."""
        if on_progress is None:
            return
        async with reporting:
            so_far = _review(numbered, [settled[number] for number in sorted(settled)])
            try:
                await on_progress({**so_far, "progress": {"done": len(settled), "total": len(claims)}})
            except Exception as error:  # noqa: BLE001 - the final review is still stored at the end
                log.warning("fact check progress not saved", error=str(error) or type(error).__name__)

    async def one(number: int, claim: dict[str, Any]) -> dict[str, Any]:
        """Checks one claim, a few at a time across the whole item."""
        where, text = sections[claim["section"] - 1]
        result = _still_judged(known.get(_wording(claim["claim"])), text)
        if result is None:
            async with gate:
                result = await _check_claim(claim, text, guidelines=guidelines, web=web, complete=complete)
        settled[number] = {"id": claim_id(number), **where, **result}
        await report()
        return settled[number]

    await report()
    results = await asyncio.gather(*(one(number, claim) for number, claim in enumerate(claims, 1)))
    log.info(
        "fact check timed",
        claims=len(claims),
        found_again=sum(1 for claim in claims if _wording(claim["claim"]) in known),
        at_once=CLAIMS_AT_ONCE,
        extract_seconds=round(extracted - started, 1),
        check_seconds=round(time.monotonic() - extracted, 1),
    )
    return _review(numbered, list(results))


def _wording(claim: str) -> str:
    """A claim's words without case or spacing, which an earlier check's claim is matched on."""
    return " ".join(claim.lower().split())


# What a check keeps of an earlier claim it finds again: its verdict, what the sources said, and a
# reason it was left for staff, so it is not put to anyone a second time.
_JUDGED_KEYS = ("claim", "verdict", "why", "checked", "evidence", "suggestion", "left")


def _still_judged(earlier: dict[str, Any] | None, text: str) -> dict[str, Any] | None:
    """An earlier verdict on the same words, if it still stands in `text`: one naming a wrong line
    stands only while that line is still there to be swapped."""
    if earlier is None:
        return None
    old = (earlier.get("suggestion") or {}).get("old")
    if old and old not in lines_of(text):
        return None
    return {key: earlier[key] for key in _JUDGED_KEYS if key in earlier}


def claim_id(number: int) -> str:
    """The id a check gives its claim numbered `number`, which a ruling names it by."""
    return f"claim-{number}"


def _numbered(sections: list[Section]) -> str:
    """The sections as the claims are listed from: numbered, in order."""
    return "\n\n".join(f"Section {number}:\n{text}" for number, (_, text) in enumerate(sections, 1))


def _hash(numbered: str) -> str:
    """A fingerprint of numbered text."""
    return hashlib.sha256(numbered.encode()).hexdigest()[:16]


def fingerprint(sections: list[Section]) -> str:
    """The `source_hash` a check of `sections` is stored with, to tell whether the text has moved since."""
    return _hash(_numbered(sections))


def _review(numbered: str, claims: list[dict[str, Any]]) -> dict[str, Any]:
    """The stored shape of a check: when, of what text, and its claims."""
    return {"checked_at": datetime.now(UTC).isoformat(), "source_hash": _hash(numbered), "claims": claims}


def checked_by_hand(
    sections: list[Section], claims: list[dict[str, Any]], *, checked_by: str
) -> dict[str, Any]:
    """The `facts` review of a check a person did themselves: each claim supported by the source
    they name, stored in the shape `check_facts` stores, with `checked_by` naming who did it.

    A claim must sit on a slide the sections have; a summary or a podcast has none."""
    slides = sum(1 for where, _ in sections if where.get("slide") is not None)
    if any(claim["slide"] is not None and claim["slide"] > slides for claim in claims):
        raise ClaimOutsideItem()
    judged = [
        {
            "id": claim_id(number),
            "slide": claim["slide"],
            **_stored_claim(
                claim["claim"],
                verdict="supported",
                why=f"Checked by hand against {claim['source']}.",
                checked=["web"],
                evidence=[
                    _finding(
                        "web",
                        {"verdict": "supported", "why": "Checked by hand.", "quote": claim["quote"]},
                        source=claim["source"],
                        url=claim["url"],
                    )
                ],
                suggestion=None,
            ),
        }
        for number, claim in enumerate(claims, 1)
    ]
    return {**_review(_numbered(sections), judged), "checked_by": checked_by}


async def check_as_deployed(
    *,
    title: str,
    sections: list[Section],
    guidelines: GuidelineIndex | None = None,
    web: GuidelineWeb | None = None,
    complete: Complete | None = None,
    on_progress: Progress | None = None,
    earlier: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """`check_facts` against this deployment's guideline library, web search and checking model,
    for whichever of them a test has not handed in. Claude checks before gpt-6.1-sol, the reverse of the
    order material is written in."""
    settings = get_settings()
    return await check_facts(
        title=title,
        sections=sections,
        guidelines=guidelines or tutor_search.guideline_index(),
        web=web or tutor_search.guideline_web(),
        complete=complete
        or (lambda prompt: model_reply(settings, prompt, system=FACT_SYSTEM, claude_first=True)),
        on_progress=on_progress,
        earlier=earlier,
    )
