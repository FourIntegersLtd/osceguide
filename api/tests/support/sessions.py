"""Session openers for tests that drive code which opens its own short sessions."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionOpener


def opener_for(session: AsyncSession) -> SessionOpener:
    """Hand the scoring steps the test's own transaction, as `job_session` hands them a real one."""

    @asynccontextmanager
    async def opener() -> AsyncIterator[AsyncSession]:
        yield session

    return opener
