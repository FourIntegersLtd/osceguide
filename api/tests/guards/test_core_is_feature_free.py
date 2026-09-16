"""`app/core` is the shared kernel. It knows nothing about any feature.

If core imports a feature, every slice that uses core silently depends on
that feature too, and the dependency order that keeps slices independently
testable is gone. import-linter enforces the same rule in CI; this test
explains it at the point of failure.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.guards._scan import CORE_ROOT, imported_modules, python_files, rel


def test_core_has_modules_to_scan() -> None:
    assert len(python_files(CORE_ROOT)) >= 8


@pytest.mark.parametrize("path", python_files(CORE_ROOT), ids=lambda p: p.name)
def test_core_never_imports_features(path: Path) -> None:
    bad = sorted(m for m in imported_modules(path) if m == "app.features" or m.startswith("app.features."))
    assert not bad, (
        f"{rel(path)} imports {bad}. core is the shared kernel; if it needs something from a "
        "feature, that thing belongs in core or in a port."
    )


def test_the_guard_would_catch_a_real_import(tmp_path: Path) -> None:
    leaky = tmp_path / "leaky.py"
    leaky.write_text("from app.features.health import router\n", encoding="utf-8")
    assert "app.features.health" in imported_modules(leaky)
