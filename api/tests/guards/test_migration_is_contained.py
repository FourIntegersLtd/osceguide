"""`app/migration` is exempt from the slice rules, so it must not spread.

It writes legacy records across every slice's tables in FK order, which is
exactly what `test_sql_lives_in_repositories` forbids everywhere else. That
exemption is only safe while the package is a leaf: nothing depends on it, so
deleting it at decommission is a delete and not a refactor.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.guards._scan import APP_ROOT, is_migration, parse, python_files, rel

MIGRATION_MODULE = "app.migration"


def _imports(tree: ast.Module) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.append(node.module)
    return found


@pytest.mark.parametrize(
    "path", [p for p in python_files(APP_ROOT) if not is_migration(p)], ids=lambda p: rel(p)
)
def test_nothing_outside_the_migration_imports_it(path: Path) -> None:
    offending = [
        name
        for name in _imports(parse(path))
        if name == MIGRATION_MODULE or name.startswith(f"{MIGRATION_MODULE}.")
    ]
    assert not offending, (
        f"{rel(path)} imports {offending}. The migration is a leaf that gets deleted; "
        "nothing in the app may depend on it."
    )


def test_the_migration_is_not_mounted() -> None:
    """A route into the importer would make a one-off script part of the API."""
    main = (APP_ROOT / "main.py").read_text(encoding="utf-8")
    assert MIGRATION_MODULE not in main
