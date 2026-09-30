"""The API contract is written, not derived.

`schemas.py` is the public shape clients depend on; the table is how we happen
to store it today. They look alike early and diverge for different reasons —
a column gets renamed, a field gets deprecated on a schedule — so the moment a
schema is generated from a row, storage changes become breaking API changes
nobody meant to ship.

So a schema module imports no repository and no domain type: it declares its
own fields. `service.py` does the mapping, in the open, where a reviewer sees
what the API promises.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.guards._scan import imported_modules, rel, slice_dirs

BANNED_SIBLINGS = {"repository", "domain"}


def schema_files() -> list[Path]:
    return sorted(p for d in slice_dirs() for p in d.glob("schemas*.py"))


def violations(path: Path) -> list[str]:
    bad: list[str] = []
    for module in imported_modules(path):
        if module.startswith("psycopg"):
            bad.append(module)
            continue
        if not module.startswith("app.features"):
            continue
        parts = module.split(".")
        if len(parts) >= 4 and parts[3] in BANNED_SIBLINGS:
            bad.append(module)
    return sorted(bad)


@pytest.mark.parametrize("path", schema_files(), ids=lambda p: rel(p))
def test_schema_does_not_import_a_repository_or_domain_type(path: Path) -> None:
    bad = violations(path)
    assert not bad, (
        f"{rel(path)} imports {bad}. Declare the response fields here and map to them in "
        "service.py, so a column rename is not an API change."
    )


@pytest.mark.parametrize("path", schema_files(), ids=lambda p: rel(p))
def test_schema_does_not_reach_another_slice(path: Path) -> None:
    slice_name = path.parent.name
    bad = sorted(
        module
        for module in imported_modules(path)
        if module.startswith("app.features") and module.split(".")[2:3] != [slice_name]
    )
    assert not bad, (
        f"{rel(path)} imports {bad}. Two slices sharing a response model couples their "
        "contracts; give each its own, or move the shared shape into core."
    )


def test_the_guard_would_catch_a_schema_built_from_a_row(tmp_path: Path) -> None:
    leaky = tmp_path / "schemas.py"
    leaky.write_text(
        "from app.features.sessions.repository import SlotRow\n"
        "from app.features.sessions.domain import SlotStatus\n"
        "from app.core.pagination import Page\n",
        encoding="utf-8",
    )
    assert violations(leaky) == [
        "app.features.sessions.domain",
        "app.features.sessions.repository",
    ]
