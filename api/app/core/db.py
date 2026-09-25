"""Database access.

- `Base` is the declarative base every slice's `models.py` extends. It carries
  a naming convention so constraints get stable names Alembic can drop later.
- `get_session` is the FastAPI dependency: one session and one transaction per
  request. The transaction commits when the handler returns and rolls back
  when it raises, so services never call commit themselves.
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
from sqlalchemy import DateTime, ForeignKey, MetaData, String, Uuid, func
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.settings import get_settings

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UUIDPrimaryKey:
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


class Timestamps:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


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
    global _engine, _session_factory
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            sqlalchemy_url(settings.database_url),
            pool_size=settings.database_pool_size,
            pool_pre_ping=True,
            echo=settings.database_echo,
        )
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    get_engine()
    assert _session_factory is not None
    return _session_factory


async def dispose_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


async def get_session() -> AsyncIterator[AsyncSession]:
    """Request-scoped unit of work: commit on success, roll back on error.

    The exception is an `AppError` marked `persist_effects`, which commits and
    still fails the request — see `AppError.persist_effects`.
    """
    from app.core.errors import AppError  # noqa: PLC0415 - avoids an import cycle
    from app.core.events import flush_pending  # noqa: PLC0415 - avoids an import cycle

    factory = get_session_factory()
    async with factory() as session:
        transaction = await session.begin()
        try:
            yield session
        except AppError as exc:
            if exc.persist_effects:
                await transaction.commit()
                await flush_pending(session)
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
            await flush_pending(session)


@asynccontextmanager
async def job_session() -> AsyncIterator[AsyncSession]:
    """A unit of work for background tasks.

    The request dependency cannot serve here: a task has no request. Same
    rule though — commit on success, roll back on error.
    """
    from app.core.events import flush_pending  # noqa: PLC0415 - avoids an import cycle

    factory = get_session_factory()
    async with factory() as session, session.begin():
        yield session
    await flush_pending(session)


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
