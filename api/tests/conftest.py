"""Test wiring.

Principles (ADR 0007):
- No in-memory store. Repository and HTTP tests run against a real Postgres.
- One database per test session, migrated once from `supabase/migrations/`.
- One transaction per test, rolled back at the end, so tests never see each
  other's rows and never need cleanup code.
- External services are fakes implementing `core.ports` protocols.

Postgres comes from `TEST_DATABASE_URL` if set, otherwise from testcontainers
(needs a running Docker daemon). If neither is available, tests that need a
database are skipped with a message rather than failing.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator

# Environment must be fixed before any app module reads settings.
os.environ["APP_ENV"] = "test"
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-not-for-production")
os.environ.setdefault("WORKER_SECRET", "test-worker-secret")
os.environ.setdefault("REDIS_DISABLED", "1")

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.core.db import Connection, close_pool, get_connection, get_pool, libpq_url  # noqa: E402
from app.core.migrations import apply_migrations  # noqa: E402
from app.core.settings import get_settings  # noqa: E402


# --------------------------------------------------------------------------
# Database lifecycle (session scope)
# --------------------------------------------------------------------------
@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    explicit = os.environ.get("TEST_DATABASE_URL")
    if explicit:
        yield libpq_url(explicit)
        return
    try:
        try:
            from testcontainers.community.postgres import PostgresContainer
        except ModuleNotFoundError:  # older testcontainers
            from testcontainers.postgres import PostgresContainer

        container = PostgresContainer("postgres:16-alpine", driver=None)
        container.start()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"No Postgres for db tests (set TEST_DATABASE_URL or start Docker): {exc}")
    try:
        yield libpq_url(container.get_connection_url())
    finally:
        container.stop()


@pytest.fixture(scope="session")
def migrated_database(database_url: str) -> str:
    os.environ["DATABASE_URL"] = database_url
    get_settings.cache_clear()
    apply_migrations(database_url)
    return database_url


@pytest_asyncio.fixture(scope="session")
async def _pool(migrated_database: str) -> AsyncIterator[None]:
    await get_pool()
    yield
    await close_pool()


# --------------------------------------------------------------------------
# Per-test transaction
# --------------------------------------------------------------------------
@pytest_asyncio.fixture
async def db_conn(_pool: None) -> AsyncIterator[Connection]:
    """A connection inside a transaction that is always rolled back."""
    pool = await get_pool()
    async with pool.connection() as conn, conn.transaction(force_rollback=True):
        yield conn


@pytest_asyncio.fixture
async def client(db_conn: Connection) -> AsyncIterator[AsyncClient]:
    """HTTP client whose requests share the test's transaction."""
    from app.main import create_app

    app = create_app()

    async def override_get_connection() -> AsyncIterator[Connection]:
        # A nested transaction is a savepoint: the request commits or rolls
        # back its own work while the outer test transaction stays open.
        async with db_conn.transaction():
            yield db_conn

    app.dependency_overrides[get_connection] = override_get_connection
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


@pytest.fixture
def settings():  # type: ignore[no-untyped-def]
    return get_settings()
