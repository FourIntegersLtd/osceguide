"""A slice reaches another slice through its service, and nothing else.

`CONTRIBUTING.md` and the handover both say so; nothing checked it, and
fourteen places had grown past it. Every one had the same excuse — "I only need
the exam's code" — and the same consequence: a table that one slice owns had
callers in nine others, so changing it meant changing them.

A service is the slice's public face. Its repository is how it happens to store
things today, its `domain` is a rule it enforces for itself, and its `models`
are rows that can drag a lazy relationship across a tenant boundary. So a
cross-slice import may name a `service*` module, `schemas`, `errors` or `jobs`,
and nothing else.

`app/migration` is exempt for the reason `_scan.is_migration` gives: its whole
job is to write every slice's tables in foreign-key order, and it is deleted
once the last tenant is across.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.guards._scan import FEATURES_ROOT, imported_modules, is_migration, parse, python_files, rel

PUBLIC_SIBLINGS = ("service", "schemas", "errors", "jobs")


def is_public(name: str) -> bool:
    """`service`, `service_worker`, `schemas`, `errors`, `jobs` — but not `services_secret`."""
    return any(name == public or name.startswith(f"{public}_") for public in PUBLIC_SIBLINGS)


def violations(path: Path, slice_name: str) -> list[str]:
    bad: list[str] = []
    tree = parse(path)
    for node in ast.walk(tree):
        if not (isinstance(node, ast.ImportFrom) and node.module and node.level == 0):
            continue
        parts = node.module.split(".")
        if len(parts) < 3 or not node.module.startswith("app.features") or parts[2] == slice_name:
            continue
        # `from app.features.x.y import z` names the module in the path, and
        # the offending module is the path itself. `from app.features.x import
        # y` names it in each alias, so the report has to name the alias too.
        if len(parts) >= 4:
            if not is_public(parts[3]):
                bad.append(node.module)
            continue
        bad.extend(f"{node.module}.{alias.name}" for alias in node.names if not is_public(alias.name))
    for module in imported_modules(path):
        parts = module.split(".")
        if (
            module.startswith("app.features")
            and len(parts) >= 4
            and parts[2] != slice_name
            and not is_public(parts[3])
        ):
            bad.append(module)
    return sorted(set(bad))


def feature_files() -> list[Path]:
    return [p for p in python_files(FEATURES_ROOT) if not is_migration(p)]


def test_there_are_files_to_check() -> None:
    assert feature_files(), "no feature files found; the guard would pass vacuously"


@pytest.mark.parametrize("path", feature_files(), ids=lambda p: rel(p))
def test_a_slice_reaches_another_only_through_its_service(path: Path) -> None:
    slice_name = path.relative_to(FEATURES_ROOT).parts[0]
    bad = violations(path, slice_name)
    assert not bad, (
        f"{rel(path)} imports {bad}. That slice owns those; ask its service for what you need. "
        "If the service has no function for it, the missing function is the point."
    )


def test_the_guard_would_catch_a_reach_into_another_slices_storage(tmp_path: Path) -> None:
    """The planted violation: three imports, two of them past the front door."""
    probe = tmp_path / "service.py"
    probe.write_text(
        "from app.features.catalog import service as catalog\n"
        "from app.features.catalog import repository as catalog_repo\n"
        "from app.features.attempts.domain import Status\n"
        "from app.features.billing import service_stripe\n",
        encoding="utf-8",
    )
    assert violations(probe, "sittings") == [
        "app.features.attempts.domain",
        "app.features.catalog.repository",
    ]
