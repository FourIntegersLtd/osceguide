"""Every org-scoped repository function takes `org_id` first.

Tenant isolation is a property of the data layer, not of whoever remembered to
add a `where` clause. If a repository function filters on `org_id`, it must
take `org_id` as its first parameter, so a call site cannot omit it.

This guard was inert for the whole build. It walked `ast.ClassDef` and matched
`org_id` inside SQL string literals — written before ADR 0013 restored
SQLAlchemy, when repositories were classes issuing raw SQL. Afterwards every
repository became module-level functions using ORM predicates
(`SlotReview.org_id == org_id`), so it scanned 21 files and inspected nothing,
green throughout. Its meta-test passed because it built a class with a SQL
string to check — a shape that exists nowhere in this codebase.

So it now looks for what is actually here: module-level functions, and
`org_id` as an attribute, a keyword or a string.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.guards._scan import parse, rel, slice_dirs


def repository_files() -> list[Path]:
    return sorted(p for d in slice_dirs() for p in d.glob("repository*.py"))


def _filters_by_org(func: ast.AST) -> bool:
    """Whether this function *narrows* a query by org.

    Setting `org_id` is not scoping: `entitlements.grant(..., org_id=None)`
    records which org granted access, and an entitlement is scoped to a user.
    Only a comparison narrows a result set, so only a comparison is looked for
    — `Model.org_id == org_id`, `filter_by(org_id=...)`, or `org_id` inside a
    `text()` fragment for the hand-written reports.
    """
    for node in ast.walk(func):
        if isinstance(node, ast.Compare):
            for side in (node.left, *node.comparators):
                if isinstance(side, ast.Attribute) and side.attr == "org_id":
                    return True
        if (
            isinstance(node, ast.Call)
            and getattr(node.func, "attr", None) == "filter_by"
            and any(k.arg == "org_id" for k in node.keywords)
        ):
            return True
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "text":
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and "org_id" in arg.value:
                    return True
    return False


# The session is always first; `org_id` must come straight after it, whether
# positionally or as the first keyword-only parameter.
_SESSION_PARAMS = frozenset({"session", "conn", "self"})


def _ordered_params(func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    positional = [a.arg for a in func.args.args if a.arg not in _SESSION_PARAMS]
    keyword_only = [a.arg for a in func.args.kwonlyargs]
    return positional + keyword_only


def violations(path: Path) -> list[str]:
    bad: list[str] = []
    for func in ast.walk(parse(path)):
        if not isinstance(func, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        if func.name.startswith("_") or not _filters_by_org(func):
            continue
        params = _ordered_params(func)
        if not params or params[0] != "org_id":
            bad.append(f"{func.name}({', '.join(params)})")
    return bad


@pytest.mark.parametrize("path", repository_files(), ids=lambda p: rel(p))
def test_org_scoped_methods_take_org_id_first(path: Path) -> None:
    bad = violations(path)
    assert not bad, f"{rel(path)}: {bad}. Put org_id first so no caller can omit it."


def test_the_guard_would_catch_a_missing_org_id(tmp_path: Path) -> None:
    """Planted in the shape this codebase actually has.

    The previous version built a class holding raw SQL, which is why it stayed
    green while the guard inspected nothing.
    """
    repo = tmp_path / "repository.py"
    repo.write_text(
        "async def leaky(session, slot_id):\n"
        "    return await session.execute(select(R).where(R.org_id == 1))\n"
        "\n"
        "async def scoped(session, org_id, slot_id):\n"
        "    return await session.execute(select(R).where(R.org_id == org_id))\n"
        "\n"
        "async def scoped_keyword_only(session, *, org_id, slot_id):\n"
        "    return await session.execute(select(R).where(R.org_id == org_id))\n"
        "\n"
        "async def filter_by_form(session, slot_id):\n"
        "    return await session.query(R).filter_by(org_id=1)\n"
        "\n"
        "async def merely_sets_it(session, *, user_id, org_id=None):\n"
        "    session.add(Grant(user_id=user_id, org_id=org_id))\n",
        encoding="utf-8",
    )

    found = violations(repo)

    assert "leaky(slot_id)" in found
    assert "filter_by_form(slot_id)" in found
    assert not [v for v in found if v.startswith("scoped")]
    # Recording which org granted something is not scoping a query by org.
    assert not [v for v in found if v.startswith("merely_sets_it")]
