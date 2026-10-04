"""Checks the clinical claims in a deck, a summary or a podcast against the guidelines.

Every claim that can be looked up (a threshold, a dose, a criterion, a target, a timing) is put
to Clinical Buddy's guideline library. Only what the library does not support goes on to the
clinical web, which is slower and dearer. Nothing here changes the material: a contradiction
comes back as a suggested replacement, with the passage and page it rests on, for a person to
accept or dismiss.

The result is the `facts` half of an item's `review`, which only platform admins are served.
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, datetime
from typing import Any

from app.core.ports import GuidelineIndex, GuidelinePassage, GuidelineWeb, WebAnswer
from app.features.media_production.script_check import Complete, slide_source
from app.features.media_production.slide_narration import json_object
from app.features.media_production.summary_text import format_summary_for_podcast

FACT_SYSTEM = (
    "You are a careful UK clinical editor checking teaching material against guidelines. "
    "You never rely on your own memory of a guideline: only on the passages you are shown. "
    "You reply with JSON only."
)
MAX_CLAIMS = 60
PASSAGES_PER_CLAIM = 5
CLAIMS_AT_ONCE = 4
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
"""

_JUDGE_PROMPT = """\
A claim in teaching material for UK doctors:
{claim}

The text it appears in:
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
that decide it, copied exactly", "why": "one sentence", "old": "...", "new": "..."}}
"evidence" is the number of the piece that decides it, or null. Give "old" and "new" only when
contradicted: "old" is the wrong words copied exactly from the text above, as short as will do,
and "new" is what should replace them. Otherwise both are null.
"""


def sections_of(kind: str, title: str, content: dict[str, Any]) -> list[str]:
    """The text to check, in the sections a claim is located by: a deck's slides, or the whole of
    a summary or a podcast as one."""
    if kind == "slide_deck":
        slides = content.get("slides")
        return (
            [slide_source(slide) for slide in slides if isinstance(slide, dict)]
            if isinstance(slides, list)
            else []
        )
    if kind == "summary":
        return [format_summary_for_podcast(title, content)]
    parts = (str(content.get("body_md") or ""), str(content.get("script") or ""))
    return ["\n\n".join(part for part in parts if part.strip())]


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
        "old": str(parsed.get("old") or ""),
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
    prompt = _JUDGE_PROMPT.format(
        claim=claim["claim"], text=text[:_SECTION_CHARACTERS], evidence_heading=heading, evidence=evidence
    )
    return _judgement(await asyncio.to_thread(complete, prompt), pieces)


async def _check_claim(
    claim: dict[str, Any],
    text: str,
    *,
    guidelines: GuidelineIndex | None,
    web: GuidelineWeb | None,
    complete: Complete,
) -> dict[str, Any]:
    """One claim's verdict, the evidence for it, and a suggested replacement if it is wrong."""
    checked: list[str] = []
    evidence: list[dict[str, Any]] = []
    verdicts: list[dict[str, Any]] = []

    if guidelines is not None:
        checked.append("guidelines")
        passages = await guidelines.search(query=claim["question"], limit=PASSAGES_PER_CLAIM, rerank=True)
        if passages:
            judged = await _judge(
                complete,
                claim,
                text,
                "Passages from the guideline library, numbered:",
                _passage_lines(passages),
                len(passages),
            )
            verdicts.append(judged)
            if judged["evidence"] is not None and judged["verdict"] != "not_found":
                passage = passages[judged["evidence"] - 1]
                evidence.append(
                    {
                        "kind": "guideline",
                        "source": passage.source,
                        "section": passage.section,
                        "page": passage.page,
                        "url": None,
                        "quote": judged["quote"] or passage.text[:_QUOTE_CHARACTERS],
                    }
                )

    settled = bool(verdicts) and verdicts[0]["verdict"] == "supported"
    if not settled and web is not None:
        found = await web.answer(question=claim["question"])
        if found is not None:
            checked.append("web")
            judged = await _judge(
                complete,
                claim,
                text,
                "What a search of the clinical web found:",
                _reference_lines(found),
                len(found.references),
            )
            verdicts.append(judged)
            if judged["verdict"] != "not_found":
                cited = found.references[judged["evidence"] - 1] if judged["evidence"] is not None else {}
                evidence.append(
                    {
                        "kind": "web",
                        "source": str(
                            cited.get("title") or cited.get("website_name") or "Clinical web search"
                        ),
                        "section": "",
                        "page": None,
                        "url": cited.get("url"),
                        "quote": judged["quote"] or found.answer[:_QUOTE_CHARACTERS],
                    }
                )

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
        # Only words that really are in the text can be swapped for the reader; anything else is advice.
        suggestion = {
            "old": wrong["old"] if wrong["old"] and wrong["old"] in text else None,
            "new": wrong["new"],
        }
    return {
        "claim": claim["claim"],
        "verdict": verdict,
        "why": decisive["why"] if decisive else "",
        "checked": checked,
        "evidence": evidence,
        "suggestion": suggestion,
    }


async def check_facts(
    *,
    kind: str,
    title: str,
    content: dict[str, Any],
    guidelines: GuidelineIndex | None,
    web: GuidelineWeb | None,
    complete: Complete,
) -> dict[str, Any]:
    """The `facts` review of an item: each clinical claim, its verdict, evidence and suggestion.

    `slide` on a claim is the slide of a deck it sits on, or `None` for a summary or podcast.
    With neither the library nor the web to ask, every claim comes back "not_checked".
    """
    sections = sections_of(kind, title, content)
    numbered = "\n\n".join(f"Section {number}:\n{text}" for number, text in enumerate(sections, 1))
    prompt = _CLAIMS_PROMPT.format(title=title, sections=numbered, limit=MAX_CLAIMS)
    claims = _claims(await asyncio.to_thread(complete, prompt), sections) if numbered.strip() else []
    gate = asyncio.Semaphore(CLAIMS_AT_ONCE)

    async def one(number: int, claim: dict[str, Any]) -> dict[str, Any]:
        """Checks one claim, a few at a time across the whole item."""
        async with gate:
            result = await _check_claim(
                claim, sections[claim["section"] - 1], guidelines=guidelines, web=web, complete=complete
            )
        slide = claim["section"] if kind == "slide_deck" else None
        return {"id": f"claim-{number}", "slide": slide, **result}

    results = await asyncio.gather(*(one(number, claim) for number, claim in enumerate(claims, 1)))
    return {
        "checked_at": datetime.now(UTC).isoformat(),
        "source_hash": hashlib.sha256(numbered.encode()).hexdigest()[:16],
        "claims": list(results),
    }
