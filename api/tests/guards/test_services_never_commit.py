"""One transaction per request, owned by `core/db.py`.

A service that commits mid-way turns "all or nothing" into "some". The
request dependency opens the transaction and commits when the handler
returns; nothing else touches commit, rollback or transaction.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.guards._scan import APP_ROOT, CORE_ROOT, attribute_names, python_files, rel

# Ending or restarting the transaction is core's job alone.
TRANSACTION_CONTROL = {"commit", "rollback", "transaction", "begin", "begin_nested"}
ALLOWED = {CORE_ROOT / "db.py"}

# `flush` only stages work inside the open transaction, so it is ordinary data
# access — a repository needs the id of a parent row before inserting a child.
# A *service* calling it is different: it is reaching into the unit of work for
# an id the repository should have handed back.
FLUSH = "flush"


def is_repository(path: Path) -> bool:
    return path.name == "repository.py" or path.name.startswith("repository_")


@pytest.mark.parametrize(
    "path", [p for p in python_files(APP_ROOT) if p not in ALLOWED], ids=lambda p: rel(p)
)
def test_only_core_db_controls_transactions(path: Path) -> None:
    bad = sorted(attribute_names(path) & TRANSACTION_CONTROL)
    assert not bad, (
        f"{rel(path)} calls {bad}. The request transaction is opened and committed by "
        "core.db.get_session; raise an AppError to roll back."
    )


def test_the_guard_would_catch_a_commit(tmp_path: Path) -> None:
    leaky = tmp_path / "service.py"
    leaky.write_text("async def save(session):\n    await session.commit()\n", encoding="utf-8")
    assert "commit" in attribute_names(leaky)


@pytest.mark.parametrize(
    "path",
    [p for p in python_files(APP_ROOT) if p not in ALLOWED and not is_repository(p)],
    ids=lambda p: rel(p),
)
def test_only_repositories_flush(path: Path) -> None:
    assert FLUSH not in attribute_names(path), (
        f"{rel(path)} calls flush. Staging writes belongs in repository.py; if a service "
        "needs a generated id, have the repository return the row it created."
    )


def test_the_guard_would_catch_a_flush_in_a_service(tmp_path: Path) -> None:
    leaky = tmp_path / "service.py"
    leaky.write_text("async def save(session):\n    await session.flush()\n", encoding="utf-8")
    assert FLUSH in attribute_names(leaky)
    assert not is_repository(leaky)
