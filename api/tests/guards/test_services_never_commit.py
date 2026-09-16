"""One transaction per request, owned by `core/db.py`.

A service that commits mid-way turns "all or nothing" into "some". The
request dependency opens the transaction and commits when the handler
returns; nothing else touches commit, rollback or transaction.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.guards._scan import APP_ROOT, CORE_ROOT, attribute_names, python_files, rel

# `flush` is included deliberately: it is the quiet way to force a write
# early, and a service that needs an id before commit wants the repository to
# return one, not to reach into the unit of work.
TRANSACTION_CONTROL = {"commit", "rollback", "transaction", "begin", "begin_nested", "flush"}
ALLOWED = {CORE_ROOT / "db.py"}


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


def test_the_guard_would_catch_a_flush(tmp_path: Path) -> None:
    leaky = tmp_path / "service.py"
    leaky.write_text("async def save(session):\n    await session.flush()\n", encoding="utf-8")
    assert TRANSACTION_CONTROL & attribute_names(leaky) == {"flush"}
