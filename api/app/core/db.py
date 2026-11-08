"""Database access.

- `Base` is the declarative base every slice's `models.py` extends. It carries
  a naming convention so constraints get stable names Alembic can drop later.
- `get_session` is the FastAPI dependency: one session and one transaction per
  request. Routes take the session as `SessionDep` (function scope), so the
  transaction commits and `flush_after_commit` runs before the response is sent. A
  default-scope `Depends(get_session)` would commit after the client already has
  its answer. Rolls back when the handler raises, so services never call commit
  themselves.
"""

from __future__ import annotations

import importlib
import pkgutil
import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import datetime
from typing import Annotated

from fastapi import Depends
from sqlalchemy import DateTime, ForeignKey, Integer, MetaData, String, Uuid, func
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.errors import Conflict
from app.core.settings import get_settings

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """The declarative base every slice's `models.py` extends."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UUIDPrimaryKey:
    """Mixin giving a table a random UUID primary key."""

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


class Timestamps:
    """Mixin giving a table `created_at`/`updated_at`, both set by Postgres."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Revisioned:
    """Mixin giving a table a `revision`, raised by one on every edit (B-15).

    A client that sends the revision it read has a stale write refused by `ensure_current`.
    The tables that check revisions are the ones using this mixin: `trainees` (roster), `exams`
    (catalog), `rubric_versions` (rubrics), `sittings` and `circuits` (sittings).
    """

    revision: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")


class StaleRevision(Conflict):
    """Someone saved this since the caller read it."""

    code = "stale_revision"
    default_message = "This was changed by someone else since you opened it. Reload and try again."


def ensure_current(expected: int | None, actual: int) -> None:
    """Refuse a write that names an older revision than the row has. No revision named, no check."""
    if expected is not None and expected != actual:
        raise StaleRevision()


def include_name(name: str | None, _type: str, _parent: object) -> bool:
    """Hide the job queue from autogenerate.

    procrastinate ships its own schema, applied verbatim by migration 0001, so
    its tables are never in `Base.metadata`. Without this filter autogenerate
    reads them as orphans and writes `drop_table` for every one.
    """
    return not (name and name.startswith("procrastinate"))


def include_object(
    _entity: object, name: str | None, type_: str, _reflected: bool, _compare_to: object
) -> bool:
    return include_name(name, type_, None)


AUTOGENERATE_FILTERS: dict[str, object] = {
    "include_name": include_name,
    "include_object": include_object,
    "compare_type": True,
}


def sqlalchemy_url(url: str) -> str:
    """Normalise any Postgres URL to the async psycopg driver.

    Railway and Supabase hand out `postgres://` or `postgresql://`;
    SQLAlchemy needs the driver spelled out.
    """
    for prefix in ("postgresql+psycopg://", "postgresql+asyncpg://", "postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


def libpq_url(url: str) -> str:
    """The same URL in the form libpq/psycopg (and procrastinate) expect."""
    return "postgresql://" + sqlalchemy_url(url)[len("postgresql+psycopg://") :]


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """The process-wide engine, created on first use."""
    global _engine, _session_factory
    if _engine is None:
        settings = get_settings()
        # No statement or idle timeouts here: PgBouncer rejects startup `options`. They are set per
        # database by the exam-day migration, and a long wait lifts the idle one (`core.jobs`).
        connect_args: dict[str, object] = {"prepare_threshold": None} if settings.database_pgbouncer else {}
        _engine = create_async_engine(
            sqlalchemy_url(settings.database_url),
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_timeout=settings.database_pool_timeout_seconds,
            pool_recycle=1800,
            connect_args=connect_args,
            pool_pre_ping=True,
            echo=settings.database_echo,
        )
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """The session factory bound to the process-wide engine, creating the engine if needed."""
    get_engine()
    assert _session_factory is not None
    return _session_factory


async def dispose_engine() -> None:
    """Close the process-wide engine's connection pool, called on shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


async def flush_after_commit(session: AsyncSession) -> None:
    """Send the events and run the cache operations the committed transaction queued."""
    from app.core.cache import flush_cache_ops  # avoids an import cycle
    from app.core.events import flush_after_commit_calls, flush_pending  # avoids an import cycle

    await flush_pending(session)
    await flush_after_commit_calls(session)
    await flush_cache_ops(session)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Request-scoped unit of work: commit on success, roll back on error.

    Routes take this as `SessionDep` (function scope), so the commit and
    `flush_after_commit` run before the response is sent. A default-scope
    `Depends(get_session)` would commit after the client already has its answer.

    The exception is an `AppError` marked `persist_effects`, which commits and
    still fails the request — see `AppError.persist_effects`.
    """
    from app.core.errors import AppError  # avoids an import cycle

    factory = get_session_factory()
    async with factory() as session:
        transaction = await session.begin()
        try:
            yield session
        except AppError as exc:
            if exc.persist_effects:
                await transaction.commit()
                await flush_after_commit(session)
            else:
                await transaction.rollback()
            raise
        except BaseException:
            await transaction.rollback()
            raise
        else:
            await transaction.commit()
            # Live updates go out here and nowhere else. Publishing inside a
            # service would wake a subscriber before the rows it is about to
            # read exist, and a rolled-back request would announce work that
            # never happened.
            await flush_after_commit(session)


@asynccontextmanager
async def job_session() -> AsyncIterator[AsyncSession]:
    """A unit of work for background tasks.

    The request dependency cannot serve here: a task has no request. Same
    rule though — commit on success, roll back on error.
    """
    factory = get_session_factory()
    async with factory() as session, session.begin():
        yield session
    await flush_after_commit(session)


@asynccontextmanager
async def savepoint(session: AsyncSession) -> AsyncIterator[None]:
    """A part of the open transaction that can fail alone.

    An error inside undoes only this part's writes, flushed or not, and the
    surrounding transaction carries on, so the caller can still record what
    went wrong.
    """
    async with session.begin_nested():
        yield


@asynccontextmanager
async def stream_session() -> AsyncIterator[AsyncSession]:
    """One snapshot's worth of reading, inside a stream that lives for minutes.

    A server-sent event stream cannot take the request session: that
    transaction would stay open for the life of the connection, holding a
    connection out of the pool and a snapshot open against vacuum for as long
    as a tab stays open. So each snapshot opens its own short transaction.
    """
    factory = get_session_factory()
    async with factory() as session, session.begin():
        yield session


SessionOpener = Callable[[], AbstractAsyncContextManager[AsyncSession]]


def get_session_opener() -> SessionOpener:
    """How a stream opens each of its short transactions.

    A dependency, not a direct call, so a test can hand a stream its own
    transaction — a test's rows live in an uncommitted transaction that a
    separately-opened connection cannot see.
    """
    return stream_session


SessionOpenerDep = Annotated[SessionOpener, Depends(get_session_opener)]

# Function scope: the commit (and flush_after_commit) runs before the response is sent.
# The default scope commits after it.
SessionDep = Annotated[AsyncSession, Depends(get_session, scope="function")]


def import_all_models() -> None:
    """Import every `app.features.<slice>.models` so Base.metadata is complete.

    Alembic autogenerate diffs the live schema against Base.metadata, and a
    table only reaches the metadata once its module has been imported.
    """
    features = importlib.import_module("app.features")
    for module_info in pkgutil.iter_modules(features.__path__):
        candidate = f"app.features.{module_info.name}.models"
        try:
            importlib.import_module(candidate)
        except ModuleNotFoundError as exc:
            if exc.name != candidate:
                raise


class Addressed:
    """Columns saying who a row is addressed to. See `app.core.audience`.

    A mixin rather than three copies: the check constraint stops a row
    claiming to be private while naming nobody.
    """

    # A plain DDL string rather than `text()`: this module declares tables and
    # never builds queries, and the guard that keeps it that way reads `text`
    # as a query builder.
    visibility: Mapped[str] = mapped_column(String(16), nullable=False, server_default="'public'")
    audience_org_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    audience_group_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("trainee_groups.id", ondelete="CASCADE")
    )


AUDIENCE_CHECK = (
    "(visibility = 'public' AND audience_org_id IS NULL AND audience_group_id IS NULL)"
    " OR (visibility = 'organisation' AND audience_org_id IS NOT NULL AND audience_group_id IS NULL)"
    " OR (visibility = 'group' AND audience_org_id IS NOT NULL AND audience_group_id IS NOT NULL)"
)
