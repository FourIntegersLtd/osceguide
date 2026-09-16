"""Every slice documents itself and no file grows past reading size.

A README with fixed headings is the first thing a new engineer reads. The
file-size cap is the platform's standing rule ("split files approaching ~200
lines"); it is what keeps a service from becoming the 2,700-line file the
legacy backend has.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.guards._scan import APP_ROOT, python_files, rel, slice_dirs

REQUIRED_HEADINGS = (
    "## Purpose",
    "## Aggregates & invariants",
    "## Routes",
    "## Jobs",
    "## Cross-slice dependencies",
)
MAX_LINES = 250


def test_there_are_slices() -> None:
    assert slice_dirs(), "no feature slices found"


@pytest.mark.parametrize("slice_dir", slice_dirs(), ids=lambda p: p.name)
def test_slice_has_a_readme_with_the_required_headings(slice_dir: Path) -> None:
    readme = slice_dir / "README.md"
    assert readme.exists(), f"{slice_dir.name}: add README.md (see CONTRIBUTING.md)"
    text = readme.read_text(encoding="utf-8")
    missing = [h for h in REQUIRED_HEADINGS if h not in text]
    assert not missing, f"{slice_dir.name}/README.md lacks {missing}"


@pytest.mark.parametrize("path", python_files(APP_ROOT), ids=lambda p: rel(p))
def test_no_file_is_longer_than_the_cap(path: Path) -> None:
    lines = len(path.read_text(encoding="utf-8").splitlines())
    assert lines <= MAX_LINES, f"{rel(path)} is {lines} lines; split it (cap {MAX_LINES})."
