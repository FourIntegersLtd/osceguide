"""Alembic environment.

Reads the database URL from app settings and diffs against `Base.metadata`,
which is filled by importing every slice's `models.py`.
"""

from __future__ import annotations

import asyncio
import threading

from alembic import context
from sqlalchemy import Connection, pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.db import Base, import_all_models, sqlalchemy_url
from app.core.settings import get_settings

config = context.config
config.set_main_option("sqlalchemy.url", sqlalchemy_url(get_settings().database_url))

import_all_models()
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _run_sync(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def _run_async() -> None:
    engine = async_engine_from_config(
        config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool
    )
    async with engine.connect() as connection:
        await connection.run_sync(_run_sync)
    await engine.dispose()


def run_migrations_online() -> None:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(_run_async())
        return
    # Called from inside a running loop (e.g. an async test): run on a fresh thread.
    error: list[BaseException] = []

    def runner() -> None:
        try:
            asyncio.run(_run_async())
        except BaseException as exc:  # noqa: BLE001
            error.append(exc)

    thread = threading.Thread(target=runner)
    thread.start()
    thread.join()
    if error:
        raise error[0]


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
