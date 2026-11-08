"""A request that waits on a model call while its transaction is open must not be dropped.

The database ends a transaction idle longer than `idle_in_transaction_session_timeout` (1 min by the
exam-day migration). `allow_long_idle` lifts that for one transaction.
"""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_engine
from app.core.jobs import allow_long_idle

pytestmark = pytest.mark.db


async def _idle_through_a_short_timeout(*, lifted: bool) -> int:
    """Hold a transaction idle for 2.5s under a 1s database timeout; return what a query then reads."""
    async with get_engine().connect() as connection:
        session = AsyncSession(bind=connection, expire_on_commit=False)
        try:
            await session.execute(
                text("select set_config('idle_in_transaction_session_timeout', '1s', true)")
            )
            if lifted:
                await allow_long_idle(session, 30)
            await asyncio.sleep(2.5)
            return int((await session.execute(text("select 7"))).scalar_one())
        finally:
            await session.close()


async def test_an_idle_transaction_is_dropped_without_allow_long_idle(_engine: None) -> None:
    with pytest.raises(DBAPIError):
        await _idle_through_a_short_timeout(lifted=False)


async def test_an_idle_transaction_survives_with_allow_long_idle(_engine: None) -> None:
    assert await _idle_through_a_short_timeout(lifted=True) == 7
