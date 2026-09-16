"""Every org-scoped repository method takes `org_id` first.

Tenant isolation is a property of the data layer, not of whoever remembered
to add a `where` clause. If a repository method's SQL mentions `org_id`, the
method must take `org_id` as its first parameter after `self`, so that a
call site cannot forget it.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.guards._scan import parse, rel, slice_dirs


def repository_files() -> list[Path]:
    return sorted(p for d in slice_dirs() for p in d.glob("repository*.py"))


def _mentions_org_id(func: ast.AST) -> bool:
    return any(
        isinstance(n, ast.Constant) and isinstance(n.value, str) and "org_id" in n.value
        for n in ast.walk(func)
    )


def violations(path: Path) -> list[str]:
    bad: list[str] = []
    for node in ast.walk(parse(path)):
        if not isinstance(node, ast.ClassDef):
            continue
        for func in node.body:
            if not isinstance(func, ast.FunctionDef | ast.AsyncFunctionDef) or func.name.startswith("_"):
                continue
            if not _mentions_org_id(func):
                continue
            params = [a.arg for a in func.args.args if a.arg != "self"] + [
                a.arg for a in func.args.kwonlyargs
            ]
            if not params or params[0] != "org_id":
                bad.append(f"{node.name}.{func.name}({', '.join(params)})")
    return bad


@pytest.mark.parametrize("path", repository_files(), ids=lambda p: rel(p))
def test_org_scoped_methods_take_org_id_first(path: Path) -> None:
    bad = violations(path)
    assert not bad, f"{rel(path)}: {bad}. Put org_id first so no caller can omit it."


def test_the_guard_would_catch_a_missing_org_id(tmp_path: Path) -> None:
    repo = tmp_path / "repository.py"
    repo.write_text(
        "class SlotRepository:\n"
        "    async def get(self, conn, slot_id):\n"
        '        return await conn.execute("select * from slots where org_id = %s and id = %s")\n'
        "    async def ok(self, org_id, conn):\n"
        '        return await conn.execute("select 1 from slots where org_id = %s")\n',
        encoding="utf-8",
    )
    assert violations(repo) == ["SlotRepository.get(conn, slot_id)"]
