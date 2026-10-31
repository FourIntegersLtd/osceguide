"""Every table says how it grows, and a table that grows per turn or without bound says what removes the rows.

`transcript_messages` reached 419 MB of a 500 MB database holding 65 MB of text: 77 rows an attempt, three
indexes, no retention story, and nobody asked what a row cost. `scripts/check_data_model.py` now asks.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import check_data_model as check  # noqa: E402

SECTION = "A table of things.\n\n| `id` | `uuid` | the key |\n"


def problems(growth_line: str | None) -> list[str]:
    body = SECTION + (f"\n{growth_line}\n" if growth_line is not None else "")
    return check.growth_problems({"things": body})


def test_a_table_with_no_declaration_fails() -> None:
    [problem] = problems(None)
    assert problem.startswith("things: declares no growth class")


def test_a_table_with_an_unknown_class_fails() -> None:
    [problem] = problems("**Growth:** sometimes")
    assert "sometimes" in problem and "per-turn" in problem


def test_a_bounded_class_needs_no_retention() -> None:
    assert problems("**Growth:** fixed. Seeded plans.") == []
    assert problems("**Growth:** per-attempt") == []


def test_a_per_turn_table_without_retention_fails() -> None:
    [problem] = problems("**Growth:** per-turn")
    assert problem.startswith("things: grows per-turn") and "Retention" in problem


def test_an_unbounded_table_without_retention_fails() -> None:
    assert len(problems("**Growth:** unbounded. Rows pile up.")) == 1


def test_a_placeholder_is_not_a_retention_story() -> None:
    for placeholder in ("none", "None yet", "TBD", "n/a", "todo", "-"):
        assert len(problems(f"**Growth:** per-turn. **Retention:** {placeholder}")) == 1, placeholder


def test_a_real_retention_story_passes() -> None:
    line = "**Growth:** per-turn. **Retention:** compacted into transcripts.messages by compact_transcripts."
    assert problems(line) == []


def test_an_acknowledged_gap_must_be_on_the_list() -> None:
    [problem] = problems("**Growth:** unbounded. **Retention:** GAP: nothing removes old rows yet.")
    assert "KNOWN_GAPS" in problem


def test_the_real_document_is_clean_and_its_gaps_only_shrink() -> None:
    from tests.guards._scan import assert_allow_list

    open_gaps = check.open_gaps()
    assert check.growth_problems(check.documented_sections(check.DOC.read_text(encoding="utf-8"))) == []
    assert_allow_list("check_data_model.KNOWN_GAPS", check.KNOWN_GAPS, check.KNOWN_GAPS_CEILING, open_gaps)
