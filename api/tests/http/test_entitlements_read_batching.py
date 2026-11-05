"""Reading a person's grants is batched: one query for the rows, one for every exam code, and a
second read in the same request is served from the session, never a second trip."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.entitlements import service as entitlements
from app.features.identity.models import User
from tests.http.test_stations_routes import a_browser, a_library_station
from tests.support.catalog import ensure_exam
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


class Statements:
    """The SQL a block of code sent, collected from the engine."""

    def __init__(self, db_session: AsyncSession) -> None:
        self.sql: list[str] = []
        self._engine = db_session.bind.sync_engine  # type: ignore[union-attr]

    def _record(self, conn, cursor, statement, *args):  # type: ignore[no-untyped-def]
        self.sql.append(statement)

    def __enter__(self) -> Statements:
        event.listen(self._engine, "before_cursor_execute", self._record)
        return self

    def __exit__(self, *exc: object) -> None:
        event.remove(self._engine, "before_cursor_execute", self._record)

    def count(self, table: str) -> int:
        return sum(1 for statement in self.sql if f"FROM {table}" in statement)


async def a_holder_of_three_grants(db_session: AsyncSession, make_actor, email: str):  # type: ignore[no-untyped-def]
    token = await a_browser(db_session, make_actor, email)
    user_id = (await db_session.execute(select(User.id).where(User.email == email))).scalar_one()
    now = datetime.now(UTC)
    for code in ("sca", "plab2", "ukmla"):
        await ensure_exam(db_session, code)
        await entitlements.grant(
            db_session,
            user_id=user_id,
            exam_code=code,
            source="purchase",
            starts_at=now - timedelta(days=1),
            ends_at=now + timedelta(days=30),
        )
    await db_session.flush()
    return token, user_id


async def test_listing_three_grants_reads_entitlements_once_and_exam_codes_once(
    db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    _, user_id = await a_holder_of_three_grants(db_session, make_actor, "three@example.com")

    with Statements(db_session) as seen:
        reads = await entitlements.list_for_user(db_session, user_id, now=datetime.now(UTC))

    assert sorted(read.exam_code for read in reads) == ["plab2", "sca", "ukmla"]
    assert seen.count("entitlements") == 1
    assert seen.count("exams") == 1


async def test_the_second_read_in_one_session_runs_no_queries(db_session: AsyncSession, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, user_id = await a_holder_of_three_grants(db_session, make_actor, "twice@example.com")
    now = datetime.now(UTC)
    first = await entitlements.list_for_user(db_session, user_id, now=now)

    with Statements(db_session) as seen:
        second = await entitlements.list_for_user(db_session, user_id, now=now)

    assert second == first
    assert seen.sql == []


async def test_a_write_makes_the_next_read_see_it(db_session: AsyncSession, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, user_id = await a_holder_of_three_grants(db_session, make_actor, "write@example.com")
    now = datetime.now(UTC)
    before = await entitlements.list_for_user(db_session, user_id, now=now)
    assert all(read.live for read in before)

    await entitlements.withdraw(db_session, before[0].id, now=now)
    await entitlements.restore(db_session, before[0].id)
    await entitlements.withdraw(db_session, before[1].id, now=now)

    after = {read.id: read for read in await entitlements.list_for_user(db_session, user_id, now=now)}
    assert after[before[1].id].live is False
    assert after[before[0].id].live is True


async def test_browsing_the_library_with_three_grants_reads_entitlements_at_most_twice(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    token, _ = await a_holder_of_three_grants(db_session, make_actor, "browse@example.com")
    await a_library_station(db_session, "Chest pain")

    with Statements(db_session) as seen:
        response = await client.get("/api/v1/stations?exam_code=sca", headers=bearer(token))

    assert response.status_code == 200, response.text
    by_id = [sql for sql in seen.sql if "FROM exams" in sql and "exams.id IN" in sql]
    assert seen.count("entitlements") <= 2, seen.sql
    # One batch for the grants' exam codes, one for the route's own exam; it was one per grant, twice.
    assert len(by_id) <= 2, "exam codes are read for all grants at once, not one per grant"
