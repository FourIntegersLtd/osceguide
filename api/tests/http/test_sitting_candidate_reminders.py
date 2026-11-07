"""Candidate reminders: a day and an hour before a sitting, once each, with a tech-check link."""

from __future__ import annotations

import re
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.notifications.models import OutboundMessage
from app.features.notifications.service import _render
from app.features.roster import service as roster
from app.features.sittings.service_notify import send_candidate_reminders
from app.features.tenancy.service_audit import SCIM_CONNECTOR
from tests.http.test_sitting_emails import EXAM_DAY, mail, placed
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

DAY_BEFORE = datetime(2026, 11, 2, 10, 30, tzinfo=UTC)  # 23.5 hours before EXAM_DAY (10:00 UTC)
HOUR_BEFORE = datetime(2026, 11, 3, 9, 10, tzinfo=UTC)  # 50 minutes before


def _visible(html: str) -> str:
    """The words a reader sees: the markup and the link addresses (routes still say /sittings) removed."""
    return re.sub(r"<[^>]*>", " ", html).lower()


async def reminders(db_session: AsyncSession) -> list[OutboundMessage]:
    rows = await db_session.execute(
        select(OutboundMessage).where(OutboundMessage.template_key == "sitting_reminder")
    )
    return sorted(rows.scalars(), key=lambda row: (row.recipient, row.payload["kind"]))


async def test_a_candidate_is_reminded_the_day_before_and_an_hour_before_once_each(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    await placed(client, db_session, make_actor)
    assert await send_candidate_reminders(db_session, now=datetime(2026, 11, 1, 9, 0, tzinfo=UTC)) == 0
    assert await reminders(db_session) == []

    assert await send_candidate_reminders(db_session, now=DAY_BEFORE) == 1
    await send_candidate_reminders(db_session, now=DAY_BEFORE.replace(hour=11))
    day = await reminders(db_session)
    assert [(row.recipient, row.payload["kind"]) for row in day] == [("cand2@example.com", "day_before")]

    await send_candidate_reminders(db_session, now=HOUR_BEFORE)
    await send_candidate_reminders(db_session, now=HOUR_BEFORE.replace(minute=40))
    both = await reminders(db_session)
    # The supervisor is not a candidate: no reminder for them.
    assert [(row.recipient, row.payload["kind"]) for row in both] == [
        ("cand2@example.com", "day_before"),
        ("cand2@example.com", "hour_before"),
    ]


async def test_nothing_is_sent_once_the_sitting_has_started(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    await placed(client, db_session, make_actor)
    assert await send_candidate_reminders(db_session, now=EXAM_DAY) == 0
    assert await send_candidate_reminders(db_session, now=datetime(2026, 11, 3, 12, 0, tzinfo=UTC)) == 0
    assert await reminders(db_session) == []


async def test_a_cancelled_or_completed_sitting_sends_no_reminder(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    admin, sitting_id, _ = await placed(client, db_session, make_actor)
    await db_session.execute(text("UPDATE sittings SET status = 'completed'"))
    assert await send_candidate_reminders(db_session, now=HOUR_BEFORE) == 0
    await db_session.execute(text("UPDATE sittings SET status = 'scheduled'"))
    cancelled = await client.post(f"/api/v1/orgs/kings/sittings/{sitting_id}/cancel", headers=bearer(admin))
    assert cancelled.status_code == 200, cancelled.text
    assert await send_candidate_reminders(db_session, now=HOUR_BEFORE) == 0
    assert await reminders(db_session) == []


async def test_a_candidate_taken_off_the_roster_is_not_reminded(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    await placed(client, db_session, make_actor)
    org_id, trainee_id = (
        await db_session.execute(text("SELECT org_id, id FROM trainees WHERE email = 'cand2@example.com'"))
    ).one()
    await roster.set_access(
        db_session, org_id, trainee_id, revoked=True, actor=SCIM_CONNECTOR, now=DAY_BEFORE
    )
    await send_candidate_reminders(db_session, now=HOUR_BEFORE)
    assert await reminders(db_session) == []


async def test_a_suspended_organisation_sends_no_reminder(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    await placed(client, db_session, make_actor)
    await db_session.execute(text("UPDATE organizations SET status = 'suspended'"))
    await send_candidate_reminders(db_session, now=HOUR_BEFORE)
    assert await reminders(db_session) == []


async def test_an_employer_candidate_is_told_in_hire_words(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    await placed(client, db_session, make_actor)
    await db_session.execute(text("UPDATE organizations SET org_type = 'employer'"))
    await send_candidate_reminders(db_session, now=HOUR_BEFORE)
    await send_candidate_reminders(db_session, now=DAY_BEFORE)
    sent = {row.payload["kind"]: row for row in await reminders(db_session)}
    assert sent["hour_before"].payload["hire"] == "1"
    hour = _render("sitting_reminder", sent["hour_before"].payload)
    assert "Your assessment starts in about an hour" in hour
    assert "sitting" not in _visible(hour)
    day = _render("sitting_reminder", sent["day_before"].payload)
    assert "Your assessment is tomorrow" in day
    scheduled = _render("sitting_scheduled", {**sent["day_before"].payload})
    assert "scheduled you for" in scheduled and "sitting" not in _visible(scheduled)


async def test_the_reminder_and_the_invitation_link_to_the_candidates_own_tech_check_page(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    await placed(client, db_session, make_actor)
    await send_candidate_reminders(db_session, now=HOUR_BEFORE)
    [reminder] = await reminders(db_session)
    scheduled = (await mail(db_session, "sitting_scheduled"))["cand2@example.com"]
    for row, template in ((reminder, "sitting_reminder"), (scheduled, "sitting_scheduled")):
        html = _render(template, row.payload)
        assert "/app/kings/trainee/tech-check" in html
        assert "Test your setup" in html
        # The link is the signed-in candidate's own page: no token, no address, no ids in it.
        link = html.split("/app/kings/trainee/tech-check", 1)[1].split('"', 1)[0]
        assert link == ""
        assert "cand2" not in link
