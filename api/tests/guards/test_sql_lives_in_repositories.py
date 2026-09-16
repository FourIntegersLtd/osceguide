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


def is_allowed(path: Path) -> bool:
    return path.name in ALLOWED_FILENAMES or path.name.startswith("repository_")


def sql_literals(path: Path) -> list[str]:
    return [s for s in string_literals(path) if SQL_SHAPE.match(s)]


def orm_query_use(path: Path) -> list[str]:
    """Query builders imported from sqlalchemy, or session execution calls."""
    found: set[str] = set()
    tree_imports = imported_modules(path)
    if any(m == "sqlalchemy" or m.startswith("sqlalchemy.") for m in tree_imports):
        found |= code_tokens(path) & QUERY_BUILDERS
    found |= attribute_names(path) & EXECUTION_METHODS
    return sorted(found)


def model_imports(path: Path) -> list[str]:
    return sorted(m for m in imported_modules(path) if m.split(".")[-1] == "models" and m.startswith("app."))


@pytest.mark.parametrize(
    "path", [p for p in python_files(APP_ROOT) if not is_allowed(p)], ids=lambda p: rel(p)
)
def test_no_sql_outside_repositories(path: Path) -> None:
    found = sql_literals(path)
    assert not found, (
        f"{rel(path)} contains SQL: {found[0][:60]!r}. Move it into the slice's repository.py; "
        "services and routers call repository methods."
    )


@pytest.mark.parametrize(
    "path", [p for p in python_files(APP_ROOT) if not is_allowed(p)], ids=lambda p: rel(p)
)
def test_no_orm_queries_outside_repositories(path: Path) -> None:
    found = orm_query_use(path)
    assert not found, (
        f"{rel(path)} builds or runs a query ({found}). An ORM call in a service is the same "
        "leak as inline SQL; give the repository a method that expresses what is wanted."
    )


@pytest.mark.parametrize(
    "path", [p for p in python_files(APP_ROOT) if not is_allowed(p)], ids=lambda p: rel(p)
)
def test_mapped_models_do_not_leave_the_repository(path: Path) -> None:
    found = model_imports(path)
    assert not found, (
        f"{rel(path)} imports {found}. A mapped class carries lazy relationships that can cross "
        "a tenant boundary with no visible query; map to a schema or a domain object instead."
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
    assert model_imports(service) == ["app.features.sessions.models"]


def test_the_guard_ignores_a_service_that_only_calls_its_repository(tmp_path: Path) -> None:
    service = tmp_path / "service.py"
    service.write_text(
        "from app.features.sessions import repository\n"
        "async def load(session, org_id):\n"
        "    return await repository.slots_for_org(session, org_id)\n",
        encoding="utf-8",
    )
    assert orm_query_use(service) == []
    assert model_imports(service) == []
