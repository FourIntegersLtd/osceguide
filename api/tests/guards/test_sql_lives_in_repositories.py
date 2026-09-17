"""Queries appear only in repositories.

The legacy b2c backend built queries inside route handlers, so every handler
carried its own copy of the same bugs. Keeping data access in `repository.py`
makes the boundary real: change a table, grep one file per slice.

Under an ORM a query is rarely a string, so matching SQL text is not enough —
`select(Slot).where(...)` in a service is the same mistake spelled differently.
This scans for three things outside a repository: SQL literals, SQLAlchemy
query construction and execution, and imports of a slice's mapped models.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.guards._scan import (
    APP_ROOT,
    attribute_names,
    code_tokens,
    imported_modules,
    is_migration,
    names_imported_from,
    python_files,
    rel,
    string_literals,
)

SQL_SHAPE = re.compile(
    r"^\s*("
    r"select\s+.+?\s+from\s|select\s+\d|with\s+\w+\s+as\s*\(|"
    r"insert\s+into\s|update\s+\S+\s+set\s|delete\s+from\s|"
    r"create\s+(table|index|schema|extension|function|type)|alter\s+table|drop\s+(table|index|schema)"
    r")",
    re.IGNORECASE | re.DOTALL,
)

# Session methods that run a query. `commit`/`rollback` belong to
# test_services_never_commit.py and are deliberately not repeated here.
#
# `session.get()` and `session.merge()` are not listed: by name they are
# indistinguishable from `dict.get` and every other `.get(` in the codebase,
# and a guard that cries wolf gets deleted. They are caught anyway, because
# `session.get(Slot, id)` has to import the mapped class, which the
# model-import check below refuses outside a repository.
EXECUTION_METHODS = {"execute", "scalar", "scalars", "stream_scalars"}
# Query builders imported from sqlalchemy.
QUERY_BUILDERS = {"select", "insert", "update", "delete", "text", "exists", "union", "union_all"}

ALLOWED_FILENAMES = {"repository.py", "models.py"}


# The query builders outside a repository, both for the same reason: they are
# one rule each, shared by every slice, and a copy per slice is a chance to get
# it subtly wrong. Keyset paging was copied into nine repositories and nine of
# them dropped rows; the audience filter decides who can see an institution's
# private conversation, which is worse to get wrong in one place out of three.
CORE_QUERY_HELPERS = {"pagination.py", "audience.py"}


def is_allowed(path: Path) -> bool:
    if path.parent.name == "core" and path.name in CORE_QUERY_HELPERS:
        return True
    return path.name in ALLOWED_FILENAMES or path.name.startswith("repository_")


def sql_literals(path: Path) -> list[str]:
    return [s for s in string_literals(path) if SQL_SHAPE.match(s)]


def orm_query_use(path: Path) -> list[str]:
    """Query builders imported from sqlalchemy, or session execution calls.

    The builders are detected by what the module imports, not by token: `update`
    and `delete` are also dict and list methods, and a guard that reports those
    is one nobody trusts.
    """
    found = names_imported_from(path, "sqlalchemy") & QUERY_BUILDERS
    found |= attribute_names(path) & EXECUTION_METHODS
    return sorted(found)


def foreign_model_imports(path: Path, slice_name: str | None) -> list[str]:
    """Imports of *another* slice's mapped models.

    A slice's own service may name its row types — it is what maps them to
    schemas. Reaching into another slice's tables is the leak: that slice owns
    its storage and may change it.
    """
    out = []
    for module in imported_modules(path):
        if not module.startswith("app.features") or module.split(".")[-1] != "models":
            continue
        parts = module.split(".")
        if slice_name is None or len(parts) < 3 or parts[2] != slice_name:
            out.append(module)
    return sorted(out)


@pytest.mark.parametrize(
    "path",
    [p for p in python_files(APP_ROOT) if not is_allowed(p) and not is_migration(p)],
    ids=lambda p: rel(p),
)
def test_no_sql_outside_repositories(path: Path) -> None:
    found = sql_literals(path)
    assert not found, (
        f"{rel(path)} contains SQL: {found[0][:60]!r}. Move it into the slice's repository.py; "
        "services and routers call repository methods."
    )


@pytest.mark.parametrize(
    "path",
    [p for p in python_files(APP_ROOT) if not is_allowed(p) and not is_migration(p)],
    ids=lambda p: rel(p),
)
def test_no_orm_queries_outside_repositories(path: Path) -> None:
    found = orm_query_use(path)
    assert not found, (
        f"{rel(path)} builds or runs a query ({found}). An ORM call in a service is the same "
        "leak as inline SQL; give the repository a method that expresses what is wanted."
    )


@pytest.mark.parametrize(
    "path", [p for p in python_files(APP_ROOT) if not is_migration(p)], ids=lambda p: rel(p)
)
def test_a_slice_does_not_import_another_slices_models(path: Path) -> None:
    parts = path.relative_to(APP_ROOT).parts
    slice_name = parts[1] if len(parts) > 2 and parts[0] == "features" else None
    found = foreign_model_imports(path, slice_name)
    assert not found, (
        f"{rel(path)} imports {found}. Another slice owns those tables and may change them; "
        "go through its service."
    )


@pytest.mark.parametrize(
    "path", [p for p in python_files(APP_ROOT) if p.name == "models.py"], ids=lambda p: rel(p)
)
def test_models_declare_columns_not_relationships(path: Path) -> None:
    """No `relationship()`, which is what makes a mapped row safe to hand to a service.

    A relationship can be traversed, and a traversal issues a query nobody
    wrote and no `org_id` filter guards — the quiet way an ORM crosses a tenant
    boundary. Foreign keys stay; loading the other side is a repository's job,
    written out, where the scoping is visible.
    """
    assert "relationship" not in code_tokens(path), (
        f"{rel(path)} declares a relationship. Load the other side in the repository, "
        "with org_id in the query."
    )


def test_the_guard_would_catch_inline_sql(tmp_path: Path) -> None:
    service = tmp_path / "service.py"
    service.write_text(
        "\n".join(
            [
                '"""select * from users in a docstring is prose, not code."""',
                "async def load(session):",
                '    return await session.execute("select id, email from users where id = 1")',
                "",
            ]
        ),
        encoding="utf-8",
    )
    assert sql_literals(service)
    clean = tmp_path / "clean.py"
    clean.write_text('MESSAGE = "update failed, try again"\n', encoding="utf-8")
    assert not sql_literals(clean)


def test_the_guard_would_catch_an_orm_query_in_a_service(tmp_path: Path) -> None:
    service = tmp_path / "service.py"
    service.write_text(
        "from sqlalchemy import select\n"
        "from app.features.sessions.models import Slot\n"
        "async def load(session):\n"
        "    return await session.execute(select(Slot))\n",
        encoding="utf-8",
    )
    assert orm_query_use(service) == ["execute", "select"]
    assert foreign_model_imports(service, "roster") == ["app.features.sessions.models"]
    assert foreign_model_imports(service, "sessions") == []


def test_the_guard_ignores_a_service_that_only_calls_its_repository(tmp_path: Path) -> None:
    service = tmp_path / "service.py"
    service.write_text(
        "from app.features.sessions import repository\n"
        "async def load(session, org_id):\n"
        "    return await repository.slots_for_org(session, org_id)\n",
        encoding="utf-8",
    )
    assert orm_query_use(service) == []
    assert foreign_model_imports(service, "sessions") == []
