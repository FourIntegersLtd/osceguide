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
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime

from sqlalchemy import DateTime, MetaData, Uuid, func
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

    procrastinate ships its own schema and migration 0001 applies it verbatim,
    so its tables are never in `Base.metadata`. Without this filter autogenerate
    reads them as orphans and writes `drop_table` for every one, which would
    take the queue with it the first time anyone adds a slice.
    """
    return not (name and name.startswith("procrastinate"))


def include_object(_obj: object, name: str | None, type_: str, _reflected: bool, _compare_to: object) -> bool:
    return include_name(name, type_, None)


AUTOGENERATE_FILTERS: dict[str, object] = {
    "include_name": include_name,
    "include_object": include_object,
    "compare_type": True,
}


def sqlalchemy_url(url: str) -> str:
    """Normalise any Postgres URL to the async psycopg driver.

    Railway and Supabase hand out `postgres://` or `postgresql://`; SQLAlchemy
    needs the driver spelled out.
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
    then still fails the request. That exists for security effects which must
    outlive the rejection that triggered them — see `AppError.persist_effects`.
    """
    from app.core.errors import AppError  # noqa: PLC0415 - avoids an import cycle

    factory = get_session_factory()
    async with factory() as session:
        transaction = await session.begin()
        try:
            yield session
        except AppError as exc:
            if exc.persist_effects:
                await transaction.commit()
            else:
                await transaction.rollback()
            raise
        except BaseException:
            await transaction.rollback()
            raise
        else:
            await transaction.commit()


@asynccontextmanager
async def job_session() -> AsyncIterator[AsyncSession]:
    """A unit of work for background tasks.

    The request dependency cannot serve here: a task has no request. Same rule
    though — commit on success, roll back on error — and it lives in this module
    so transaction control stays in one place.
    """
    factory = get_session_factory()
    async with factory() as session, session.begin():
        yield session


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
