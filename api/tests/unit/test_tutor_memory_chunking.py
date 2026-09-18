"""Oracle: `b2c-api/b2c/shared/utils/management_text_utils.py`.

Where a chunker cuts decides what the tutor can quote. A boundary moved by one
sentence changes which passage a question retrieves, and the tutor then reads
out a different answer for the same question — a behaviour change with no
diff anywhere near it. So the port is pinned to the original's output on a
captured document rather than to a description of what it ought to do.

The fixture was produced by executing the legacy module's own source, not by
retyping it, and is checked in because those repositories are going away.
"""

from __future__ import annotations

import json
import pathlib

from app.features.tutor_memory import chunking

ORACLE = json.loads(
    (pathlib.Path(__file__).parent.parent / "fixtures/tutor_memory/chunker_oracle.json").read_text()
)


def test_the_port_cuts_where_the_legacy_chunker_cut() -> None:
    chunks = chunking.chunk(ORACLE["text"])

    assert [{"index": c.index, "section": c.section, "text": c.text} for c in chunks] == ORACLE["chunks"]


def test_the_sections_are_named_after_the_headings_they_follow() -> None:
    """The section is what a citation says, so it is part of the contract."""
    sections = [c.section for c in chunking.chunk(ORACLE["text"])]

    assert sections[0] == chunking.OVERVIEW
    assert "red_flags" in sections
    # Whatever follows the last recognised heading is cut by size, and those
    # windows are all one section: there is no heading left to name them after.
    assert sections[-1] == chunking.REMAINDER


def test_a_section_body_is_not_capped_at_the_chunk_size() -> None:
    """A legacy quirk, pinned so that changing it has to be deliberate.

    Only the tail after the last heading goes through the size pass, so a long
    section between two headings is emitted whole — 3815 characters here,
    against a 1800 limit. It is recorded in `docs/OPEN-QUESTIONS.md` as T-1
    rather than fixed inside a port whose whole point is that it changed
    nothing.
    """
    longest = max(chunking.chunk(ORACLE["text"]), key=lambda c: len(c.text))

    assert len(longest.text) > chunking.MAX_CHUNK_CHARS
    assert longest.section == "brief_management"


def test_nothing_in_gives_nothing_out() -> None:
    assert chunking.chunk("") == []
    assert chunking.chunk("   ") == []


def test_a_document_with_no_headings_is_cut_by_size_alone() -> None:
    text = "One plain paragraph about a cough. " * 200

    chunks = chunking.chunk(text)

    assert len(chunks) > 1
    assert {c.section for c in chunks} == {chunking.REMAINDER}
    assert [c.index for c in chunks] == list(range(len(chunks)))
    # Each window carries the tail of the one before it, so a sentence split
    # across a boundary is whole in the second.
    assert all(len(c.text) <= chunking.MAX_CHUNK_CHARS for c in chunks)


def test_a_short_leading_fragment_is_dropped_rather_than_indexed() -> None:
    """A heading and a stray clause retrieve noise and quote as a non-answer."""
    chunks = chunking.chunk("Tiny. Red flags Ask about chest pain that radiates to the jaw.")

    assert [c.section for c in chunks] == [chunking.REMAINDER]
