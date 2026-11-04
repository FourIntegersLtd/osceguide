"""The load-test seed refuses any database that is not local or staging."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parents[2] / "scripts" / "seed_loadtest.py"
_spec = importlib.util.spec_from_file_location("seed_loadtest", _PATH)
assert _spec
assert _spec.loader
seed_loadtest = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(seed_loadtest)


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg://u:p@localhost:5432/db",
        "postgresql://u:p@127.0.0.1/db",
        "postgresql://u:p@platform-postgres-staging.railway.internal:5432/db",
    ],
)
def test_allows_local_and_staging(url: str) -> None:
    seed_loadtest.refuse_unless_safe(url)


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://u:p@platform-postgres-production.railway.internal/db",
        "postgresql://u:p@db.example.com/staging",
    ],
)
def test_refuses_anything_else(url: str) -> None:
    with pytest.raises(SystemExit):
        seed_loadtest.refuse_unless_safe(url)


def test_emails_are_load_test_addresses() -> None:
    assert seed_loadtest.email_for(7) == "trainee7@load-test.example.com"
