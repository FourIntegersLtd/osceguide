"""Test wiring.

Principles (CONTRIBUTING.md):
- No in-memory store. Repository and HTTP tests run against a real Postgres.
- One database per test session, migrated once with Alembic.
- One app per test session. Building it registers 659 routes and costs most
  of a second, which rebuilt per test was 17 of the suite's 18 minutes.
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
# Station images need a bucket configured for the route to be reachable at
# all; the S3 client itself is faked at its seam in the tests that use it.
os.environ.setdefault("AWS_REGION", "eu-west-2")
# Signing a media link is local arithmetic but needs *some* key pair. Set, not `setdefault`, so a
# test never depends on a developer's real credentials (CI has none) or reaches the real bucket.
os.environ["AWS_ACCESS_KEY_ID"] = "AKIAFAKEFORTESTS"
os.environ["AWS_SECRET_ACCESS_KEY"] = "fake-secret-for-tests"
# A local `.env` OpenAI key would otherwise make `build_material_index` look
# configured, and the tutor would claim it searched material it never read.
# The real key is kept aside for `tests/e2e`, whose worker needs it; only its
# `e2e_env` fixture puts it back, and e2e runs alone (`-m e2e`).
os.environ.setdefault("E2E_OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
os.environ["OPENAI_API_KEY"] = ""
# A local Anthropic key is blanked too: `stations/station_ai.py` falls back to it,
# so "no model configured" tests would call the real model.
os.environ["ANTHROPIC_API_KEY"] = ""
# Set, not `setdefault`: a developer's `.env` namespaces their agents so two
# people can share one LiveKit project, and that prefix must not change what
# the dispatch tests assert the worker is called.
os.environ["LIVEKIT_AGENT_NAMESPACE"] = ""
# A local .env key would send tutor tools to the real guideline library.
os.environ["CLINICAL_BUDDY_SERVICE_KEY"] = ""
# The legacy login bridge. Set here so the exchange route is exercised in
# its configured state; `test_legacy_exchange_routes` covers the unset one
# by overriding the setting, because an unset secret must fail closed.
os.environ.setdefault("LEGACY_CONSUMER_JWT_SECRET", "legacy-consumer-test-secret")
os.environ.setdefault("LEGACY_INSTITUTION_JWT_SECRET", "legacy-institution-test-secret")

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.db import (  # noqa: E402
    dispose_engine,
    get_engine,
    get_session,
    get_session_opener,
    libpq_url,
    sqlalchemy_url,
)
from app.core.settings import get_settings  # noqa: E402
from tests.support.declared_codes import install as install_declared_code_check  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

# Pinned, and pinned to a *pgvector* image rather than stock Postgres: the
# tutor's material index is a `vector` column, so a container without the
# extension fails at `alembic upgrade head` and takes every database test
# with it. Keep in step with `docker-compose.yml`.
POSTGRES_IMAGE = "pgvector/pgvector:pg16"


# --------------------------------------------------------------------------
# Database lifecycle (session scope)
# --------------------------------------------------------------------------
@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    explicit = os.environ.get("TEST_DATABASE_URL")
    if explicit:
        worker = os.environ.get("PYTEST_XDIST_WORKER", "main")
        if worker != "main":
            # Each xdist worker gets its own database. The shared CI database
            # serialised database tests across workers: even though each test
            # rolls back, row-level locks block concurrent writes to the same
            # tables, so four workers ran no faster than one.
            worker_url = _create_worker_database(explicit, worker)
            try:
                yield sqlalchemy_url(worker_url)
            finally:
                _drop_worker_database(explicit, worker_url)
            return
        yield sqlalchemy_url(explicit)
        return
    try:
        try:
            from testcontainers.community.postgres import PostgresContainer
        except ModuleNotFoundError:  # older testcontainers
            from testcontainers.postgres import PostgresContainer

        # Must carry `vector`: the tutor_memory migration creates the
        # extension, so a stock image fails at `alembic upgrade head` and
        # every database test with it.
        container = PostgresContainer(POSTGRES_IMAGE, driver=None)
        container.start()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"No Postgres for db tests (set TEST_DATABASE_URL or start Docker): {exc}")
    try:
        yield sqlalchemy_url(container.get_connection_url())
    finally:
        container.stop()


def _worker_db_name(base: str, worker_id: str) -> str:
    """Derive a per-worker database name from the base URL and worker id."""
    from urllib.parse import urlparse

    parsed = urlparse(base)
    return f"{parsed.path.lstrip('/')}_pytest_{worker_id}"


def _create_worker_database(base_url: str, worker_id: str) -> str:
    """Create a per-worker database and return its URL."""
    import psycopg

    worker_db = _worker_db_name(base_url, worker_id)
    admin_url = base_url.rsplit("/", 1)[0] + "/postgres"

    with psycopg.connect(admin_url, autocommit=True) as conn:
        conn.execute(f'DROP DATABASE IF EXISTS "{worker_db}"')
        conn.execute(f'CREATE DATABASE "{worker_db}"')

    return base_url.rsplit("/", 1)[0] + f"/{worker_db}"


def _drop_worker_database(base_url: str, worker_url: str) -> None:
    """Drop a per-worker database after the session ends."""
    from urllib.parse import urlparse

    import psycopg

    worker_db = urlparse(worker_url).path.lstrip("/")
    admin_url = base_url.rsplit("/", 1)[0] + "/postgres"

    with psycopg.connect(admin_url, autocommit=True) as conn:
        conn.execute(f'DROP DATABASE IF EXISTS "{worker_db}" WITH (FORCE)')


def _create_supabase_api_roles(database_url: str) -> None:
    """Make the test database look like Supabase: `anon` and `authenticated` exist and every
    new table is granted to them by default, so the RLS migration's revoke has work to do.
    Roles are cluster-wide, so tolerate them existing already and parallel workers racing."""
    import psycopg

    sql = """
    DO $$
    DECLARE r text;
    BEGIN
      FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        BEGIN
          EXECUTE format('CREATE ROLE %I NOLOGIN', r);
        EXCEPTION WHEN duplicate_object THEN NULL;
        END;
        EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO %I', r);
      END LOOP;
    END $$;
    """
    with psycopg.connect(libpq_url(database_url), autocommit=True) as conn:
        conn.execute(sql)


@pytest.fixture(scope="session")
def migrated_database(database_url: str) -> str:
    from alembic.config import Config

    from alembic import command

    os.environ["DATABASE_URL"] = database_url
    get_settings.cache_clear()
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    _create_supabase_api_roles(database_url)
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


# The transaction of the test now running. The shared app's session overrides
# read it on every request, which is what lets one app serve every test while
# each test keeps a transaction of its own. Set by the `app` fixture.
_current_test_session: AsyncSession | None = None


def _test_session() -> AsyncSession:
    """The running test's transaction; a request outside a test is a wiring bug, not a database."""
    if _current_test_session is None:
        raise RuntimeError("a request was made outside a test's `app` fixture")
    return _current_test_session


@pytest.fixture(scope="session")
def built_app():  # type: ignore[no-untyped-def]
    """The real app, built once per session and wired to whichever test is running.

    `create_app()` registers every route and builds each one's pydantic
    schemas, most of a second of CPU. The suite's ~2,500 database tests used to
    do that each, which was 17 of its 18 minutes and the reason running it in
    parallel on a four-core runner gained nothing. The overrides below are the
    app's base state; `app` restores them after each test.
    """
    from app.main import create_app

    built = create_app()
    install_declared_code_check(built)

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        # Mirrors `core.db.get_session`, including the `persist_effects` rule
        # and the after-commit publish: if this diverged, a test could prove
        # behaviour production does not have.
        from app.core.db import flush_after_commit
        from app.core.errors import AppError

        db_session = _test_session()
        try:
            yield db_session
        except AppError as exc:
            if exc.persist_effects:
                await db_session.commit()
                await flush_after_commit(db_session)
            else:
                await db_session.rollback()
            raise
        except Exception:
            await db_session.rollback()
            raise
        else:
            await db_session.commit()  # releases the savepoint; the outer transaction stays open
            await flush_after_commit(db_session)

    @asynccontextmanager
    async def override_stream_session() -> AsyncIterator[AsyncSession]:
        """Lend a stream the test's own transaction.

        `core.db.stream_session` opens a connection of its own, which in a test
        cannot see rows written inside the outer transaction that is rolled
        back at the end. Overridden rather than patched, which is why
        `get_session_opener` is a dependency at all.
        """
        yield _test_session()

    built.dependency_overrides[get_session] = override_get_session
    built.dependency_overrides[get_session_opener] = lambda: override_stream_session
    return built


@pytest_asyncio.fixture
async def app(built_app, db_session: AsyncSession):  # type: ignore[no-untyped-def]
    """The shared app, pointed at this test's transaction for the test's duration.

    A fixture of its own because two clients need it: the in-process one below
    for ordinary requests, and a real server for streams. Tests add overrides
    of their own (a fake room agent, a fake checkout); those are dropped on the
    way out so no test inherits another's fakes.
    """
    global _current_test_session
    base_overrides = dict(built_app.dependency_overrides)
    _current_test_session = db_session
    try:
        yield built_app
    finally:
        _current_test_session = None
        built_app.dependency_overrides.clear()
        built_app.dependency_overrides.update(base_overrides)


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
    from datetime import UTC, datetime

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
        exam_code: str | None = None,
        signed_in: bool = False,
    ) -> str:
        user = await repository.create_user(
            db_session,
            email=email,
            name=email,
            password_hash=None,
            is_platform_admin=platform_admin,
            exam_code=exam_code,
        )
        if signed_in:  # otherwise the account is invited and has not accepted
            user.last_login_at = datetime.now(UTC)
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


@pytest_asyncio.fixture
async def seat_redis(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[object]:
    """A real Redis for the voice seat scripts, under keys no other test shares.

    The Lua scripts are what is under test, so a fake that re-implements them
    would only prove the fake. Redis stays disabled for the rest of the app;
    only the voice seat and Cloud slot counters are pointed here, since they
    share one script runner. Skipped when no Redis is reachable
    (`docker compose up -d` serves one on :6380), as the `db` tests skip
    without Postgres.
    """
    import uuid

    from redis.asyncio import Redis

    from app.features.voice import capacity, seats

    url = os.environ.get("TEST_REDIS_URL", "redis://localhost:6380/15")
    client = Redis.from_url(url, decode_responses=True, socket_connect_timeout=0.5)
    try:
        await client.ping()
    except Exception:  # noqa: BLE001 - any failure to reach it means skip
        await client.aclose()
        pytest.skip(f"no Redis at {url}; the voice seat scripts need a real one")

    # Per-test keys, because xdist runs tests from this file side by side.
    prefix = f"test:{uuid.uuid4().hex}"
    keys = {
        "CLOUD_SLOTS_KEY": f"{prefix}:cloud",
        "SEATS_KEY": f"{prefix}:seats",
        "QUEUE_KEY": f"{prefix}:queue",
        "SEEN_KEY": f"{prefix}:seen",
    }
    for constant, key in keys.items():
        monkeypatch.setattr(seats, constant, key)
    monkeypatch.setattr(capacity, "CLOUD_SLOTS_KEY", keys["CLOUD_SLOTS_KEY"])
    monkeypatch.setattr(capacity, "get_redis", lambda: client)
    try:
        yield client
    finally:
        await client.delete(*keys.values())
        await client.aclose()


@pytest.fixture
def voice_tokens(client: AsyncClient):  # type: ignore[no-untyped-def]
    """Replace the LiveKit adapter with a recording fake.

    An override rather than a patch, so the seam is the one production uses.
    """
    from app.features.voice.service import get_voice_tokens
    from tests.support.fakes import FakeVoiceTokens

    fake = FakeVoiceTokens()
    client._transport.app.dependency_overrides[get_voice_tokens] = lambda: fake  # type: ignore[attr-defined]
    return fake


@pytest.fixture
def agents(client: AsyncClient):  # type: ignore[no-untyped-def]
    """A room-agents fake (patients, mic permissions) in place of LiveKit; files may override it."""
    from app.features.voice.service import get_room_agents
    from tests.support.fakes import FakeRoomAgents

    fake = FakeRoomAgents()
    client._transport.app.dependency_overrides[get_room_agents] = lambda: fake  # type: ignore[attr-defined]
    return fake


@pytest.fixture(autouse=True)
def _fresh_local_rate_windows() -> Iterator[None]:
    """Sign-in counts per process when Redis is off; one test's attempts must not count in the next.

    Looked up in `sys.modules` so a test that never loaded the module does not import it (and read
    settings) before the database url is set."""
    import sys

    def clear() -> None:
        """Empty the process-local windows if the limiter has been imported."""
        module = sys.modules.get("app.core.rate_limit")
        if module is not None:
            module._local_windows.clear()

    clear()
    yield
    clear()
