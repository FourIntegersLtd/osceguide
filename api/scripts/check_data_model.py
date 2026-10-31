"""Is `docs/DATA-MODEL.md` still true?

The document asks for this in its own preamble: a checker that imports
`Base.metadata`, diffs the tables and columns against the headings and field
rows, and fails on anything present in one and absent from the other. Until it
existed, the rule "a migration and this document change in the same commit" was
a promise — and a document nothing checks drifts: the port's status page once
described slices as complete while their rules had no caller.

Deliberately tolerant about *form* and strict about *presence*. The document
writes a column four ways, and each reads better in its place than a uniform
row would:

    | `status` | `varchar(32) not null` | ...        a field row
    | `started_at` / `completed_at` | ... |          a pair on one row
    `name varchar(200) not null`                     a sentence, for join tables
    | `status`, `published_at/by`, `archived_at/by` | as for template versions |

So a column counts as documented when its name appears inside any backticked
span of that table's section, with `x_at/by` expanded to `x_at` and `x_by`. A
column mentioned nowhere at all is the drift worth failing on.

It also asks every table how it grows. `transcript_messages` reached 419 MB of a 500 MB database that
held 65 MB of text (77 rows an attempt, three indexes, no retention story) because nobody asked what a
row cost. So each section declares

    **Growth:** per-turn. **Retention:** compacted into transcripts.messages by compact_transcripts.

with a class from GROWTH_CLASSES, and a table that grows `per-turn` or `unbounded` must also say what
removes or compacts its rows. A retention that is a placeholder fails. A table whose honest answer is
"nothing yet" writes `**Retention:** GAP: <what is missing>` and is listed in KNOWN_GAPS with the same
reason: the list is bounded and only shrinks, so a gap is visible and cannot quietly grow.

What this cannot check is the half that rots silently: whether the *reason*
given for a delete rule or a partial index is still the real one. Read those.

    python scripts/check_data_model.py
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("APP_ENV", "test")

DOC = ROOT / "docs" / "DATA-MODEL.md"

# Carried by the `Timestamps` and `UUIDPrimaryKey` mixins and documented once,
# under Conventions, rather than on all 57 tables.
MIXIN_COLUMNS = frozenset({"id", "created_at", "updated_at"})
# The `Addressed` mixin, documented once for the same reason.
ADDRESSED_COLUMNS = frozenset({"visibility", "audience_org_id", "audience_group_id"})
# procrastinate owns its own schema; it is applied from the vendored file.
FOREIGN_PREFIX = "procrastinate"


def documented_sections(markdown: str) -> dict[str, str]:
    """Each `### \\`table\\`` heading and the prose beneath it."""
    parts = re.split(r"\n#{2,3} `([a-z_]+)`\n", markdown)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts), 2)}


def mentioned_names(section: str) -> set[str]:
    """Every identifier named inside a backticked span of one section.

    Backticks only: prose says "suspension writes the status", and counting
    that as documentation of a `status` column would make this agree with
    anything.
    """
    names: set[str] = set()
    for span in re.findall(r"`([^`]+)`", section):
        # `published_at/by` is the document's shorthand for both columns.
        expanded = re.sub(r"\b(\w+)_at/by\b", r"\1_at \1_by", span)
        names.update(re.findall(r"[a-z_][a-z0-9_]*", expanded))
    return names


GROWTH_CLASSES = ("fixed", "per-user", "per-org", "per-attempt", "per-turn", "unbounded")
NEEDS_RETENTION = ("per-turn", "unbounded")
GROWTH_LINE = re.compile(r"\*\*Growth:\*\*\s*([A-Za-z-]+)\.?(.*?)(?:\n[ \t]*\n|\Z)", re.S)
RETENTION = re.compile(r"\*\*Retention:\*\*\s*(.+)", re.S)
PLACEHOLDER = re.compile(r"^(none|n/?a|tbd|todo|-+|unknown|later|nothing)\b[\s.]*$", re.I)
MIN_RETENTION_WORDS = 4

# Tables that grow per turn or without bound and have no retention yet: `table -> what is missing`.
# Each section says `**Retention:** GAP: ...`. The ceiling only shrinks; closing a gap removes its entry.
KNOWN_GAPS: dict[str, str] = {
    "site_messages": ("public contact form rows are never deleted or archived; nothing bounds a spam run."),
    "refresh_chains": ("revoked and expired chains are never deleted; one row per sign-in, forever."),
    "refresh_tokens": (
        "every rotation adds a row and spent or expired tokens are never deleted; the fastest- "
        "growing auth table."
    ),
    "password_reset_tokens": ("used and expired tokens are never deleted; one row per reset request."),
    "audit_log": (
        "append-only by design with no archive or age limit; needs a retention period decision (a "
        "legal one) and an archive step."
    ),
    "stripe_events": (
        "one row per acted-on webhook delivery, kept forever; only the recent window is needed for "
        "replay protection."
    ),
    "partner_arrivals": (
        "one row per public link click, never pruned and not bounded by anything a user does; a bot "
        "can inflate it."
    ),
    "practice_queue_entries": (
        "expiry only flips status to expired; the row is never deleted, one per queue join."
    ),
    "assistant_transcript_messages": (
        "turns of help sessions are kept and never pruned; other kinds store none."
    ),
    "learning_events": (
        "written by the browser on every read, listen or practice and deleted only when the user "
        "asks to be forgotten."
    ),
    "outbound_messages": (
        "sent and failed rows are kept forever (only erasure requests delete unsent mail); needs an "
        "age-based prune of sent rows."
    ),
}
KNOWN_GAPS_CEILING = 11


def _declaration(section: str) -> tuple[str | None, str]:
    """`(growth class, the rest of that paragraph)`, the class None when the section declares none."""
    found = GROWTH_LINE.search(section)
    return (found.group(1).lower(), found.group(2)) if found else (None, "")


def _retention(rest: str) -> str | None:
    found = RETENTION.search(rest)
    return found.group(1).strip() if found else None


def _is_gap(retention: str | None) -> bool:
    return retention is not None and retention.upper().startswith("GAP")


def growth_problems(sections: dict[str, str]) -> list[str]:
    """Each table's growth declaration that is missing, unknown, or lacks the retention its class needs."""
    problems: list[str] = []
    for name in sorted(sections):
        growth, rest = _declaration(sections[name])
        if growth is None:
            problems.append(
                f"{name}: declares no growth class. Add `**Growth:** <{' | '.join(GROWTH_CLASSES)}>`."
            )
        elif growth not in GROWTH_CLASSES:
            problems.append(f"{name}: growth class `{growth}` is not one of {', '.join(GROWTH_CLASSES)}.")
        elif growth in NEEDS_RETENTION:
            retention = _retention(rest)
            if _is_gap(retention):
                if name not in KNOWN_GAPS:
                    problems.append(
                        f"{name}: declares a retention GAP but is not in KNOWN_GAPS. Close the gap."
                    )
            elif (
                retention is None
                or PLACEHOLDER.match(retention)
                or len(retention.split()) < MIN_RETENTION_WORDS
            ):
                problems.append(
                    f"{name}: grows {growth} and declares no retention. Say what removes or compacts its "
                    "rows: `**Retention:** ...`."
                )
    return problems


def open_gaps() -> set[str]:
    """Tables whose section currently declares a retention GAP."""
    sections = documented_sections(DOC.read_text(encoding="utf-8"))
    return {name for name, section in sections.items() if _is_gap(_retention(_declaration(section)[1]))}


def drift() -> list[str]:
    from app.core.db import Base, import_all_models

    import_all_models()
    markdown = DOC.read_text(encoding="utf-8")
    sections = documented_sections(markdown)
    tables = {
        table.name: table
        for table in Base.metadata.sorted_tables
        if not table.name.startswith(FOREIGN_PREFIX)
    }

    problems: list[str] = []
    for name in sorted(set(tables) - set(sections)):
        problems.append(f"{name}: no `### `{name}`` section. Add one.")
    for name in sorted(set(sections) - set(tables)):
        problems.append(f"{name}: documented, but no such table. Delete the section.")

    for name in sorted(set(tables) & set(sections)):
        named = mentioned_names(sections[name])
        expected = set(tables[name].columns.keys()) - MIXIN_COLUMNS
        if set(tables[name].columns.keys()) >= ADDRESSED_COLUMNS:
            expected -= ADDRESSED_COLUMNS
        absent = sorted(column for column in expected if column not in named)
        if absent:
            problems.append(f"{name}: columns not mentioned in its section: {', '.join(absent)}")

    problems += growth_problems({name: sections[name] for name in sorted(set(tables) & set(sections))})

    counted = re.search(r"(\d+) tables across (\d+) slices", markdown)
    if counted and int(counted.group(1)) != len(tables):
        problems.append(f"the header says {counted.group(1)} tables; there are {len(tables)}.")
    return problems


def main() -> None:
    problems = drift()
    if problems:
        print("docs/DATA-MODEL.md has drifted from the schema:\n")  # noqa: T201
        for problem in problems:
            print(f"  - {problem}")  # noqa: T201
        print(  # noqa: T201
            "\nA migration and this document change in the same commit; see its preamble."
        )
        raise SystemExit(1)
    print("docs/DATA-MODEL.md agrees with the schema.")  # noqa: T201


if __name__ == "__main__":
    main()
