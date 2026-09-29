"""Oracle: `b2c-api/b2c/shared/utils/management_text_utils.py`.

Where a chunker cuts decides what the tutor can quote. A boundary moved by one
sentence changes which passage a question retrieves, and the tutor then reads
out a different answer for the same question — a behaviour change with no
diff anywhere near it. So the port is pinned to the original's output on a
captured document rather than to a description of what it ought to do.

The fixture was produced by executing the legacy module's own source, not by
retyping it, and is checked in because those repositories are going away. Its
chunks were regenerated once, deliberately, for T-1: the long section between
two headings that the legacy chunker emitted whole is now three windows under
the same heading. Every other chunk is the legacy output unchanged.
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


def test_a_section_body_is_capped_at_the_chunk_size() -> None:
    """T-1: a long section between two headings is cut by size too.

    The legacy chunker size-cut only the tail after the last heading, so the
    brief-management section here went out whole at 3815 characters against an
    1800 limit, and the embedding model silently truncated it. Its windows keep
    the heading's name, because the section is what a citation says.
    """
    chunks = chunking.chunk(ORACLE["text"])

    assert all(len(c.text) <= chunking.MAX_CHUNK_CHARS for c in chunks)
    management = [c for c in chunks if c.section == "brief_management"]
    assert len(management) > 1
    # Consecutive windows overlap, so nothing said at a boundary is lost.
    assert management[0].text[-chunking.OVERLAP_CHARS // 2 :] in management[1].text


def test_a_short_section_is_one_passage_as_before() -> None:
    """Only a section over the limit is cut; everything else is the legacy output."""
    chunks = chunking.chunk(
        "An opening line that is long enough to be kept as its own overview passage. "
        "Red flags Ask about chest pain that radiates to the jaw, and about breathlessness at rest. "
        "Examinations Pulse."
    )

    assert [c.section for c in chunks] == [chunking.OVERVIEW, "red_flags", chunking.REMAINDER]


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
