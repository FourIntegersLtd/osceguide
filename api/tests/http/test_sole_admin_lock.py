"""The sole-administrator guard locks before it counts, so two closures cannot both pass it."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.identity import repository as identity_repo
from app.features.tenancy import service_memberships
from app.features.tenancy.errors import LastAdministrator
from tests.http.test_tenancy_routes import member_token, seed_org

pytestmark = pytest.mark.db


async def test_refusing_the_only_administrator_locks_the_admin_memberships_first(
    client: AsyncClient,
    make_actor,  # type: ignore[no-untyped-def]
    db_session: AsyncSession,
) -> None:
    org_id = await seed_org(client, make_actor)
    await member_token(make_actor, org_id, "kings", "institution_admin")
    admin = await identity_repo.user_by_email(db_session, "institution_admin-kings@example.com")
    assert admin is not None
    statements: list[str] = []

    def record(conn, cursor, statement, *args):  # type: ignore[no-untyped-def]
        statements.append(statement)

    sync_engine = db_session.bind.sync_engine  # type: ignore[union-attr]
    event.listen(sync_engine, "before_cursor_execute", record)
    try:
        with pytest.raises(LastAdministrator):
            await service_memberships.ensure_not_sole_admin_anywhere(db_session, admin.id)
    finally:
        event.remove(sync_engine, "before_cursor_execute", record)

    locking = [s for s in statements if "FROM memberships" in s and "FOR UPDATE" in s]
    assert locking, statements
