"""Cutting a piece of study material into passages that can be embedded.

Behaviour-identical to the legacy chunker on purpose: a different cut would retrieve
differently for the same question. `tests/unit/test_tutor_memory_chunking.py` holds it to
the original. Turning a document into text is `sources.py`'s job; this only recognises
section headings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ~400 tokens, which is what the legacy sparse model's 512-token limit left
# room for once the query was allowed for. Kept at the legacy value so the
# boundaries land in the same places.
MAX_CHUNK_CHARS = 1800
OVERLAP_CHARS = 100

# A chunk shorter than this is a heading and a stray clause, which retrieves
# noisily and reads as a non-answer when the tutor quotes it.
MIN_SECTION_CHARS = 50

# The headings a piece of clinical material actually uses. Recognising them is
# what makes a retrieved passage quotable: a cut made mid-section gives the
# tutor half a thought to read out.
_SECTIONS = re.compile(
    r"\b(Red flags|Examinations|Brief management|Psychosocial|First-Line|Long-Term|"
    r"Medications|Non-pharmacological|Follow-up|History|Physical exam|Investigations|"
    r"Impact|Education|Resources|Social Support|Explanation|Assessment)\b",
    re.IGNORECASE,
)

OVERVIEW = "overview"
REMAINDER = "management"


@dataclass(frozen=True)
class Chunk:
    """One passage, and the section heading it was found under."""

    index: int
    section: str
    text: str


def chunk(text: str) -> list[Chunk]:
    """Split `text` into passages: by heading where there are headings, then by size.

    The two passes are not alternatives. A document with headings is cut at
    them first, and whatever follows the last heading is then cut by size --
    which is the case that matters, because the management plan is usually the
    long tail after the last recognised heading.
    """
    if not text:
        return []

    chunks: list[Chunk] = []
    position, section = 0, OVERVIEW
    while position < len(text):
        match = _SECTIONS.search(text, position)
        if match is None:
            break
        body = text[position : match.start()].strip()
        if len(body) > MIN_SECTION_CHARS:
            chunks.append(Chunk(index=len(chunks), section=section, text=body))
        section = _section_name(match.group(1))
        position = match.end()

    remainder = text[position:].strip() if position < len(text) else text
    if not remainder:
        return chunks
    chunks.extend(_by_size(remainder, first_index=len(chunks)))
    return chunks


def _section_name(heading: str) -> str:
    return heading.lower().replace(" ", "_").replace("-", "_")[:30]


def _by_size(text: str, *, first_index: int) -> list[Chunk]:
    """Fixed-width windows that stop at a sentence, overlapping by a little.

    The overlap is what stops a sentence split across two windows from being
    retrievable from neither: each window carries the tail of the one before
    it, so a thought that straddles a boundary is whole in the second.
    """
    chunks: list[Chunk] = []
    start = 0
    while start < len(text):
        end = start + MAX_CHUNK_CHARS
        if end < len(text):
            end = _break_before(text, start, end)
        body = text[start:end].strip()
        if body:
            chunks.append(Chunk(index=first_index + len(chunks), section=REMAINDER, text=body))
        start = end - OVERLAP_CHARS if end < len(text) else len(text)
    return chunks


def _break_before(text: str, start: int, end: int) -> int:
    """The last sentence end before `end`, or the last space, or `end` itself.

    A space is looked for only when the window holds no full stop at all, not when it holds
    one in an unusable place — otherwise a window opening on a full stop would be cut short
    instead of left at full width, moving every boundary after it.
    """
    found = text.rfind(".", start, end + 1)
    if found == -1:
        found = text.rfind(" ", start, end + 1)
    return found + 1 if found > start else end
