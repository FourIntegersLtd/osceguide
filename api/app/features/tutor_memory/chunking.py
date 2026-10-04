"""Cutting a piece of study material into passages that can be embedded.

Ported from the legacy chunker, and identical to it except in one place (T-1): a section
between two headings longer than `MAX_CHUNK_CHARS` is now cut by size as well, where the
legacy chunker emitted it whole. A different cut retrieves differently for the same
question, so `tests/unit/test_tutor_memory_chunking.py` pins the output on a captured
document. Turning a document into text is `sources.py`'s job; this only recognises section
headings.
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
    them first, and every piece is then cut by size: each section keeps its
    heading's name across its windows, and whatever follows the last heading is
    the `management` tail -- usually the longest piece of all.

    The legacy chunker size-cut only that tail, so a long section between two
    headings became one passage past the embedding model's limit, silently
    truncated when it was embedded (T-1).
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
            chunks.extend(_by_size(body, first_index=len(chunks), section=section))
        section = _section_name(match.group(1))
        position = match.end()

    remainder = text[position:].strip() if position < len(text) else text
    if not remainder:
        return chunks
    chunks.extend(_by_size(remainder, first_index=len(chunks), section=REMAINDER))
    return chunks


def _section_name(heading: str) -> str:
    return heading.lower().replace(" ", "_").replace("-", "_")[:30]


def _by_size(text: str, *, first_index: int, section: str) -> list[Chunk]:
    """Fixed-width windows that stop at a sentence, overlapping by a little, all
    filed under `section`. Text within the limit comes back as one window.

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
            chunks.append(Chunk(index=first_index + len(chunks), section=section, text=body))
        start = end - OVERLAP_CHARS if end < len(text) else len(text)
    return chunks


def _break_before(text: str, start: int, end: int) -> int:
    """The last sentence end before `end`, or the last space, or `end` itself.

    A space is looked for only when the window holds no full stop at all, not when it holds
    one in an unusable place — otherwise a window opening on a full stop would be cut short
    instead of left at full width, moving every boundary after it.

    A break inside the overlap is unusable too: the next window starts `OVERLAP_CHARS`
    before it, which is at or before this one's start, so the cut never advances. Every
    window after the first opens with the full stop the last one ended on, so prose with
    no full stop for a window's width (a long bulleted list) looped here for ever.
    """
    found = text.rfind(".", start, end + 1)
    if found == -1:
        found = text.rfind(" ", start, end + 1)
    return found + 1 if found >= start + OVERLAP_CHARS else end
