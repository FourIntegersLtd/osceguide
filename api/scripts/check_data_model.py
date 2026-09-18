"""Is `docs/DATA-MODEL.md` still true?

The document asks for this in its own preamble: a checker that imports
`Base.metadata`, diffs the tables and columns against the headings and field
rows, and fails on anything present in one and absent from the other. Until it
existed, the rule "a migration and this document change in the same commit" was
a promise, and `docs/STATUS.md` is the standing reminder of what happens to a
document nothing checks — slices were described as complete while their rules
had no caller.

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
