"""SQL appears only in repositories and the migration runner.

The legacy b2c backend built queries inside route handlers, so every handler
carried its own copy of the same bugs. Keeping SQL in `repository.py` makes
the data-access boundary real: change a table, grep one file per slice.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.guards._scan import APP_ROOT, python_files, rel, string_literals

SQL_SHAPE = re.compile(
    r"^\s*("
    r"select\s+.+?\s+from\s|select\s+\d|with\s+\w+\s+as\s*\(|"
    r"insert\s+into\s|update\s+\S+\s+set\s|delete\s+from\s|"
    r"create\s+(table|index|schema|extension|function|type)|alter\s+table|drop\s+(table|index|schema)"
    r")",
    re.IGNORECASE | re.DOTALL,
)

ALLOWED_FILENAMES = {"repository.py", "migrations.py"}


def is_allowed(path: Path) -> bool:
    return path.name in ALLOWED_FILENAMES or path.name.startswith("repository_")


def sql_literals(path: Path) -> list[str]:
    return [s for s in string_literals(path) if SQL_SHAPE.match(s)]


@pytest.mark.parametrize(
    "path", [p for p in python_files(APP_ROOT) if not is_allowed(p)], ids=lambda p: rel(p)
)
def test_no_sql_outside_repositories(path: Path) -> None:
    found = sql_literals(path)
    assert not found, (
        f"{rel(path)} contains SQL: {found[0][:60]!r}. Move it into the slice's repository.py; "
        "services and routers call repository methods."
    )


def test_the_guard_would_catch_inline_sql(tmp_path: Path) -> None:
    service = tmp_path / "service.py"
    service.write_text(
        "\n".join(
            [
                '"""select * from users in a docstring is prose, not code."""',
                "async def load(conn):",
                '    return await conn.execute("select id, email from users where id = %s", (1,))',
                "",
            ]
        ),
        encoding="utf-8",
    )
    assert sql_literals(service)
    clean = tmp_path / "clean.py"
    clean.write_text('MESSAGE = "update failed, try again"\n', encoding="utf-8")
    assert not sql_literals(clean)
