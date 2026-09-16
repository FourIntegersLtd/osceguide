"""`domain.py` holds the rules and touches nothing.

An invariant that needs a database to prove is an invariant nobody tests. The
state machines, policy predicates and validation rules live in plain Python so
`tests/unit` can exercise every branch in milliseconds with no container
running. The moment a domain module imports psycopg, FastAPI or an HTTP client,
its rules can only be tested through a stack, and they stop being tested.

This also keeps the dependency arrow honest: `service.py` composes domain
decisions with repository data, so domain never reaches back out for either.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.guards._scan import imported_modules, rel, slice_dirs

# Anything that performs or describes I/O. `app.core.db` is listed explicitly
# because importing a connection type is how the drift usually starts.
BANNED_PREFIXES = (
    "psycopg",
    "fastapi",
    "starlette",
    "httpx",
    "aiohttp",
    "requests",
    "redis",
    "procrastinate",
    "boto3",
    "stripe",
    "openai",
    "anthropic",
    "app.core.db",
    "app.core.redis",
    "app.core.jobs",
)


def domain_files() -> list[Path]:
    return sorted(p for d in slice_dirs() for p in d.glob("domain*.py"))


def violations(path: Path) -> list[str]:
    return sorted(
        module
        for module in imported_modules(path)
        if any(module == p or module.startswith(f"{p}.") for p in BANNED_PREFIXES)
    )


@pytest.mark.parametrize("path", domain_files(), ids=lambda p: rel(p))
def test_domain_imports_no_io(path: Path) -> None:
    bad = violations(path)
    assert not bad, (
        f"{rel(path)} imports {bad}. Domain modules are pure: the rule belongs here, "
        "the data fetching belongs in repository.py, and service.py joins them."
    )


@pytest.mark.parametrize("path", domain_files(), ids=lambda p: rel(p))
def test_domain_does_not_reach_another_slice(path: Path) -> None:
    slice_name = path.parent.name
    bad = sorted(
        module
        for module in imported_modules(path)
        if module.startswith("app.features") and module.split(".")[2:3] != [slice_name]
    )
    assert not bad, (
        f"{rel(path)} imports {bad}. A domain rule that needs another slice is a rule "
        "in the wrong slice, or a value the service should pass in as an argument."
    )


def test_the_guard_would_catch_a_domain_that_queries(tmp_path: Path) -> None:
    leaky = tmp_path / "domain.py"
    leaky.write_text(
        "import psycopg\nfrom app.core.db import Connection\nfrom app.core.pagination import Page\n",
        encoding="utf-8",
    )
    assert violations(leaky) == ["app.core.db", "psycopg"]
