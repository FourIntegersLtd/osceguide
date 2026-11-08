"""Deleting a candidate's data at the institution's request: personal data goes, marks and results stay."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts.models import AssessmentResult, Attempt, TranscriptMessage
from app.features.results.models import CandidateResultRevision, ResultAppeal
from app.features.roster.models import Trainee
from app.features.tenancy.models import AuditEntry
from tests.http.test_results_appeals import REASON, appeal_route, released_result
from tests.support.tokens import bearer
from tests.support.transcripts import add_turns, an_attempt

pytestmark = pytest.mark.db


async def give_transcript(db_session: AsyncSession, org_id, user_id):  # type: ignore[no-untyped-def]
    """A finished attempt of this person in this organisation, with a transcript and a mark."""
    attempt_id = await an_attempt(db_session)
    await add_turns(db_session, attempt_id, 3)
    attempt = await db_session.get(Attempt, attempt_id)
    assert attempt is not None
    attempt.org_id = org_id
    attempt.user_id = user_id
    attempt.status = "evaluated"
    db_session.add(
        AssessmentResult(
            attempt_id=attempt_id,
            framework_id="f",
            policy_version="v1",
            payload={"overall": 7},
            scored_at=datetime.now(UTC),
        )
    )
    await db_session.flush()
    return attempt_id


async def test_deleting_a_candidates_data_keeps_the_marks_and_the_result_history(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin, _second, _second_id, candidate, sitting, trainee = await released_result(
        client, make_actor, db_session
    )
    row = await db_session.get(Trainee, trainee)
    assert row is not None and row.user_id is not None
    email = row.email
    route = f"/api/v1/orgs/kings/candidates/{trainee}/erase-data"

    wrong = await client.post(route, json={"confirmation": "someone-else@example.com"}, headers=bearer(admin))
    assert wrong.status_code == 422
    assert wrong.json()["code"] == "confirmation_mismatch"
    await db_session.refresh(row)
    assert row.email == email, "a mistyped confirmation changes nothing"

    # After the refused request: a refusal rolls back whatever the test had not yet committed.
    attempt_id = await give_transcript(db_session, org_id, row.user_id)
    from app.features.notifications.models import OutboundMessage

    sent = OutboundMessage(
        recipient=email,
        subject="Result",
        template_key="candidate_result_released",
        payload={"org_slug": "kings"},
        idempotency_key=f"k-{trainee}",
        status="sent",
    )
    elsewhere = OutboundMessage(
        recipient=email,
        subject="Other",
        template_key="candidate_result_released",
        payload={"org_slug": "another-school"},
        idempotency_key=f"k2-{trainee}",
        status="pending",
    )
    db_session.add_all([sent, elsewhere])
    await db_session.flush()
    done = await client.post(route, json={"confirmation": email.upper()}, headers=bearer(admin))
    assert done.status_code == 200, done.text
    await db_session.refresh(sent)
    assert sent.recipient != email, "mail already sent stops naming the person"
    await db_session.refresh(elsewhere)
    assert elsewhere.recipient == email, "another organisation's mail to them is not ours to touch"
    assert done.json()["attempts_cleared"] == 1

    await db_session.refresh(row)
    assert (row.first_name, row.last_name, row.anonymised_at is not None) == (None, None, True)
    assert row.email.endswith("@anonymised.invalid")
    turns = await db_session.scalars(
        select(TranscriptMessage).where(TranscriptMessage.attempt_id == attempt_id)
    )
    assert list(turns) == []
    attempt = await db_session.get(Attempt, attempt_id)
    assert attempt is not None
    await db_session.refresh(attempt)
    assert attempt.content_erased_at is not None
    marks = await db_session.scalars(
        select(AssessmentResult).where(AssessmentResult.attempt_id == attempt_id)
    )
    assert [m.payload for m in marks] == [{"overall": 7}], "the mark stays"
    revisions = (
        await db_session.scalars(
            select(CandidateResultRevision)
            .where(CandidateResultRevision.trainee_id == trainee)
            .order_by(CandidateResultRevision.revision)
        )
    ).all()
    assert [(r.revision, r.assessment_outcome, r.rationale) for r in revisions] == [
        (1, "pass", "[erased]"),
        (2, "pass", "[erased]"),
        (3, "pass", "[erased]"),
    ]

    again = await client.post(route, json={"confirmation": email}, headers=bearer(admin))
    assert again.status_code == 200
    assert again.json()["attempts_cleared"] == 0
    audited = (
        await db_session.scalars(
            select(AuditEntry).where(
                AuditEntry.org_id == org_id, AuditEntry.action == "candidate_data.erased"
            )
        )
    ).all()
    assert len(audited) == 1, "repeating it writes no second audit row"
    assert email not in str(audited[0].meta) + str(audited[0].summary), "the audit row holds no personal data"


async def test_data_is_kept_while_an_appeal_is_open_and_appeal_text_is_scrubbed_after(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin, _second, _second_id, candidate, sitting, trainee = await released_result(
        client, make_actor, db_session
    )
    row = await db_session.get(Trainee, trainee)
    assert row is not None
    asked = await client.post(appeal_route(sitting), json={"reason": REASON}, headers=bearer(candidate))
    route = f"/api/v1/orgs/kings/candidates/{trainee}/erase-data"

    blocked = await client.post(route, json={"confirmation": row.email}, headers=bearer(admin))
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "appeal_open"

    await client.post(
        f"/api/v1/orgs/kings/appeals/{asked.json()['id']}/decline",
        json={"reason": "The checklist used was the published one."},
        headers=bearer(admin),
    )
    done = await client.post(route, json={"confirmation": row.email}, headers=bearer(admin))
    assert done.status_code == 200, done.text
    assert done.json()["appeals_scrubbed"] == 1
    kept = (await db_session.scalars(select(ResultAppeal))).one()
    assert (kept.reason, kept.decision_note, kept.status) == ("[erased]", None, "declined")


async def test_only_an_administrator_of_the_organisation_may_delete_a_candidates_data(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from tests.http.test_results_routes import org_with_admin

    _org, _admin, _second, _id, candidate, _sitting, trainee = await released_result(
        client, make_actor, db_session
    )
    _, outsider = await org_with_admin(client, make_actor, slug="guys")
    route = f"/api/v1/orgs/kings/candidates/{trainee}/erase-data"
    body = {"confirmation": "x@example.com"}
    assert (await client.post(route, json=body, headers=bearer(outsider))).status_code == 403
    assert (await client.post(route, json=body, headers=bearer(candidate))).status_code == 403
