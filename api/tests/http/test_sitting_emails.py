"""E-1: the institution emails. A scheduled sitting, a reviewer named, and the morning of the exam."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.notifications.models import OutboundMessage
from app.features.sittings.service_notify import send_exam_day_reminders
from tests.http.test_examiner_transcript_routes import an_examiner
from tests.http.test_sittings_routes import a_template_version
from tests.support.sittings import a_trainee, org_with_admin, published_station
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

EXAM_DAY = datetime(2026, 11, 3, 10, 0, tzinfo=UTC)


async def placed(
    client: AsyncClient, db_session: AsyncSession, make_actor, *, scheduled: bool = True
) -> tuple[str, str, str]:  # type: ignore[no-untyped-def]
    """A sitting (dated or not), one trainee, a named supervisor; returns admin, sitting, circuit ids."""
    org_id, admin = await org_with_admin(client, make_actor)
    template = await a_template_version(client, admin)
    body: dict[str, object] = {"name": "Finals", "programme_id": str(template), "mode": "exam"}
    if scheduled:
        body["scheduled_for"] = EXAM_DAY.isoformat()
    sitting = (await client.post("/api/v1/orgs/kings/sittings", json=body, headers=bearer(admin))).json()
    station = await published_station(client, admin, "kings", "Sore knee")
    await a_trainee(db_session, "cand@example.com")
    candidate = await a_trainee(db_session, "cand2@example.com")
    supervisor, _ = await an_examiner(db_session, org_id, "sup@example.com")
    created = await client.post(
        f"/api/v1/orgs/kings/sittings/{sitting['id']}/circuits",
        json={
            "name": "Room 1",
            "trainee_ids": [str(candidate)],
            "station_version_ids": [station],
            "supervisor_user_id": str(supervisor),
        },
        headers=bearer(admin),
    )
    assert created.status_code == 201, created.text
    return admin, sitting["id"], created.json()["id"]


async def mail(db_session: AsyncSession, template: str) -> dict[str, OutboundMessage]:
    """The queued mail of one template, by recipient."""
    rows = (
        await db_session.execute(select(OutboundMessage).where(OutboundMessage.template_key == template))
    ).scalars()
    return {row.recipient: row for row in rows}


async def test_placing_a_trainee_on_a_dated_sitting_emails_them_the_date(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    _, sitting_id, _ = await placed(client, db_session, make_actor)
    sent = await mail(db_session, "sitting_scheduled")
    assert list(sent) == ["cand2@example.com"]
    assert sent["cand2@example.com"].payload["sitting_id"] == sitting_id
    assert sent["cand2@example.com"].payload["scheduled_at"].startswith("2026-11-03")


async def test_an_undated_sitting_sends_no_schedule_email(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    await placed(client, db_session, make_actor, scheduled=False)
    assert await mail(db_session, "sitting_scheduled") == {}


async def test_naming_a_supervisor_emails_them_the_circuit(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    _, _, circuit_id = await placed(client, db_session, make_actor)
    sent = await mail(db_session, "review_assigned")
    assert list(sent) == ["sup@example.com"]
    assert sent["sup@example.com"].payload["circuit_id"] == circuit_id


async def test_the_exam_day_reminder_goes_out_from_the_morning_and_only_once(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    await placed(client, db_session, make_actor)
    early = datetime(2026, 11, 3, 6, 59, tzinfo=UTC)
    morning = datetime(2026, 11, 3, 7, 0, tzinfo=UTC)
    assert await send_exam_day_reminders(db_session, now=early) == 0
    assert await mail(db_session, "exam_day_reminder") == {}

    assert await send_exam_day_reminders(db_session, now=morning) == 1
    await send_exam_day_reminders(db_session, now=datetime(2026, 11, 3, 15, 0, tzinfo=UTC))
    assert sorted(await mail(db_session, "exam_day_reminder")) == ["cand2@example.com", "sup@example.com"]
    count = len(
        list(
            (
                await db_session.execute(
                    select(OutboundMessage).where(OutboundMessage.template_key == "exam_day_reminder")
                )
            ).scalars()
        )
    )
    assert count == 2


async def test_no_reminder_on_another_day(client: AsyncClient, db_session: AsyncSession, make_actor) -> None:  # type: ignore[no-untyped-def]
    await placed(client, db_session, make_actor)
    assert await send_exam_day_reminders(db_session, now=datetime(2026, 11, 4, 9, 0, tzinfo=UTC)) == 0
    assert await mail(db_session, "exam_day_reminder") == {}


async def test_a_cancelled_sitting_sends_no_reminder(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    admin, sitting_id, _ = await placed(client, db_session, make_actor)
    cancelled = await client.post(f"/api/v1/orgs/kings/sittings/{sitting_id}/cancel", headers=bearer(admin))
    assert cancelled.status_code == 200, cancelled.text
    assert await send_exam_day_reminders(db_session, now=datetime(2026, 11, 3, 9, 0, tzinfo=UTC)) == 0
    assert await mail(db_session, "exam_day_reminder") == {}
