"""A router parses, calls one service, returns a schema.

Routers may import their own slice's `schemas`, `service` and `errors`, and
anything in `core`. Never another slice, never a repository, never `domain`.
The legacy b2c route files were 1,600 lines because nothing stopped them.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.guards._scan import imported_modules, rel, slice_dirs

ALLOWED_SIBLINGS = {"schemas", "service", "errors"}


def router_files() -> list[Path]:
    return sorted(p for d in slice_dirs() for p in d.glob("router*.py"))


def violations(path: Path, slice_name: str) -> list[str]:
    bad: list[str] = []
    for module in imported_modules(path):
        if not module.startswith("app.features"):
            continue
        parts = module.split(".")
        if len(parts) < 3 or parts[2] != slice_name or len(parts) >= 4 and parts[3] not in ALLOWED_SIBLINGS:
            bad.append(module)
    return sorted(bad)


@pytest.mark.parametrize("path", router_files(), ids=lambda p: rel(p))
def test_router_imports_only_its_own_schemas_service_and_errors(path: Path) -> None:
    bad = violations(path, path.parent.name)
    assert not bad, (
        f"{rel(path)} imports {bad}. Routers reach other slices through their own service, "
        "and never touch a repository or domain module directly."
    )


def test_the_guard_would_catch_a_fat_router(tmp_path: Path) -> None:
    router = tmp_path / "router.py"
    router.write_text(
        "from app.features.sessions.repository import SlotRepository\n"
        "from app.features.roster.service import x\n",
        encoding="utf-8",
    )
    assert violations(router, "sessions") == [
        "app.features.roster.service",
        "app.features.sessions.repository",
    ]
