"""Test wiring.

Principles (ADR 0009):
- No in-memory store. Repository and HTTP tests run against a real Postgres.
- One database per test session, migrated once with Alembic.
- One transaction per test, rolled back at the end, so tests never see each
  other's rows and never need cleanup code.
- External services are fakes implementing `core.ports` protocols.

Postgres comes from `TEST_DATABASE_URL` if set, otherwise from testcontainers
(needs a running Docker daemon). If neither is available, tests marked `db`
are skipped with a message rather than failing.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from pathlib import Path

# Environment must be fixed before any app module reads settings.
os.environ["APP_ENV"] = "test"
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-not-for-production")
os.environ.setdefault("WORKER_SECRET", "test-worker-secret")
os.environ.setdefault("REDIS_DISABLED", "1")
os.environ.setdefault("LIVEKIT_URL", "wss://livekit.test")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_test_secret")

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.db import (  # noqa: E402
    dispose_engine,
    get_engine,
    get_session,
    get_session_opener,
    sqlalchemy_url,
)
from app.core.settings import get_settings  # noqa: E402
from tests.support.declared_codes import install as install_declared_code_check  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------------
# Database lifecycle (session scope)
# --------------------------------------------------------------------------
@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    explicit = os.environ.get("TEST_DATABASE_URL")
    if explicit:
        yield sqlalchemy_url(explicit)
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
        yield sqlalchemy_url(container.get_connection_url())
    finally:
        container.stop()


@pytest.fixture(scope="session")
def migrated_database(database_url: str) -> str:
    from alembic.config import Config

    from alembic import command

    os.environ["DATABASE_URL"] = database_url
    get_settings.cache_clear()
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    command.upgrade(cfg, "head")
    return database_url


@pytest_asyncio.fixture(scope="session")
async def _engine(migrated_database: str) -> AsyncIterator[None]:
    get_engine()
    yield
    await dispose_engine()


# --------------------------------------------------------------------------
# Per-test transaction
# --------------------------------------------------------------------------
@pytest_asyncio.fixture
async def db_session(_engine: None) -> AsyncIterator[AsyncSession]:
    engine = get_engine()
    async with engine.connect() as connection:
        outer = await connection.begin()
        session = AsyncSession(
            bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        try:
            yield session
        finally:
            await session.close()
            await outer.rollback()


@pytest_asyncio.fixture
async def app(db_session: AsyncSession):  # type: ignore[no-untyped-def]
    """The real app, wired to the test's transaction.

    A fixture of its own because two clients need it: the in-process one below
    for ordinary requests, and a real server for streams.
    """
    from app.main import create_app

    built = create_app()
    install_declared_code_check(built)

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        # Mirrors `core.db.get_session`, including the `persist_effects` rule
        # and the after-commit publish: if this diverged, a test could prove
        # behaviour production does not have.
        from app.core.errors import AppError
        from app.core.events import flush_pending

        try:
            yield db_session
        except AppError as exc:
            if exc.persist_effects:
                await db_session.commit()
                await flush_pending(db_session)
            else:
                await db_session.rollback()
            raise
        except Exception:
            await db_session.rollback()
            raise
        else:
            await db_session.commit()  # releases the savepoint; the outer transaction stays open
            await flush_pending(db_session)

    @asynccontextmanager
    async def override_stream_session() -> AsyncIterator[AsyncSession]:
        """Lend a stream the test's own transaction.

        `core.db.stream_session` opens a connection of its own, which in a test
        cannot see rows written inside the outer transaction that is rolled
        back at the end. Overridden rather than patched, which is why
        `get_session_opener` is a dependency at all.
        """
        yield db_session

    built.dependency_overrides[get_session] = override_get_session
    built.dependency_overrides[get_session_opener] = lambda: override_stream_session
    return built


@pytest_asyncio.fixture
async def client(app) -> AsyncIterator[AsyncClient]:  # type: ignore[no-untyped-def]
    """HTTP client whose requests share the test's transaction."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


@pytest_asyncio.fixture
async def streaming_client(app) -> AsyncIterator[AsyncClient]:  # type: ignore[no-untyped-def]
    """A client talking to a real server on a real socket.

    `ASGITransport` runs the application to completion and hands back the
    collected body, which for a `text/event-stream` route means waiting for a
    response that is designed never to end. Nothing about a stream can be
    tested through it — not the first frame, not a pushed one — so these tests
    run uvicorn in this process, on an ephemeral port, against the same app
    object and the same transaction as every other test.
    """
    import uvicorn

    config = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning", lifespan="off")
    server = uvicorn.Server(config)
    serving = asyncio.create_task(server.serve())
    try:
        while not server.started:
            await asyncio.sleep(0.01)
        port = server.servers[0].sockets[0].getsockname()[1]
        async with AsyncClient(base_url=f"http://127.0.0.1:{port}", timeout=30.0) as http:
            yield http
    finally:
        server.should_exit = True
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(serving, timeout=10)


@pytest_asyncio.fixture
async def make_actor(db_session: AsyncSession):  # type: ignore[no-untyped-def]
    """Create a real user and mint a token for them.

    Tokens are self-describing, so it is tempting to mint one for an invented
    id — but anything that writes an audit row has a foreign key to `users`,
    and a token for a person who does not exist is not a case production can
    reach. The fixture keeps the two in step.
    """
    from app.core.auth import Membership
    from app.features.identity import repository
    from app.features.tenancy import repository as tenancy_repository
    from tests.support.tokens import mint_token

    async def _make(
        email: str = "user@example.com",
        *,
        platform_admin: bool = False,
        memberships: tuple[Membership, ...] = (),
        active_org_slug: str | None = None,
    ) -> str:
        user = await repository.create_user(
            db_session,
            email=email,
            name=email,
            password_hash=None,
            is_platform_admin=platform_admin,
        )
        # The membership rows are written, not just claimed. A token asserting
        # a membership no table held was fine while every check read the
        # claims; it stopped being fine when `switch-workspace` started
        # reading the database, which is the whole point of that change.
        for membership in memberships:
            await tenancy_repository.add_membership(
                db_session,
                org_id=membership.org_id,
                user_id=user.id,
                role=membership.role,
                product_surface=membership.surface,
            )
        await db_session.flush()
        return mint_token(
            user_id=user.id,
            email=email,
            memberships=memberships,
            active_org_slug=active_org_slug,
            platform_admin=platform_admin,
        )

    return _make


@pytest.fixture
def settings():  # type: ignore[no-untyped-def]
    return get_settings()
