"""Non-verbal feedback: consent, ingest and the candidate-only read."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select, text

from app.features.attempts import domain, repository
from app.features.attempts.models import AttemptNonverbalBatch, AttemptNonverbalSummary
from app.features.identity import repository as identity_repo
from app.features.tenancy import repository as tenancy_repo
from tests.support.catalog import ensure_exam
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

NOW_MS = int(datetime.now(UTC).timestamp() * 1000)


def _batch(seq: int = 0) -> dict:
    """One valid batch of two samples."""
    sample = {"at_ms": NOW_MS, "face": True, "away": False, "yaw": 3, "pitch": -2, "smile": 10, "nod": False}
    return {"seq": seq, "client_sent_at_ms": NOW_MS, "samples": [sample, {**sample, "at_ms": NOW_MS + 1000}]}


async def _attempt(db_session, email: str, *, kind: str = "practice", org_id: uuid.UUID | None = None):
    """A user's attempt of this kind, created straight in the repository."""
    user = await identity_repo.user_by_email(db_session, email)
    assert user is not None
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    source_attempt_id = None
    if kind == "debrief":  # needs a source attempt; an exam slot needs a whole circuit, same refusal
        source_attempt_id = (
            await repository.create_attempt(db_session, user_id=user.id, exam_id=exam.id, kind="practice")
        ).id
    attempt = await repository.create_attempt(
        db_session,
        user_id=user.id,
        exam_id=exam.id,
        kind=kind,
        org_id=org_id,
        source_attempt_id=source_attempt_id,
    )
    return attempt.id


async def _stored(db_session, attempt_id: uuid.UUID) -> int:
    """How many batch rows this attempt holds."""
    return int(
        await db_session.scalar(
            select(func.count())
            .select_from(AttemptNonverbalBatch)
            .where(AttemptNonverbalBatch.attempt_id == attempt_id)
        )
        or 0
    )


async def _consent(client, token: str, consented: bool = True):
    """PUT the person's consent."""
    return await client.put(
        "/api/v1/me/nonverbal-consent",
        json={"consented": consented, "version": "2026-11"},
        headers=bearer(token),
    )


async def test_read_without_consent_is_supported_but_off(client, db_session, make_actor):
    token = await make_actor("nv-read@example.com")
    attempt_id = await _attempt(db_session, "nv-read@example.com")
    response = await client.get(f"/api/v1/attempts/{attempt_id}/nonverbal", headers=bearer(token))
    assert response.status_code == 200
    body = response.json()
    assert (body["supported"], body["consented"], body["state"]) == (True, False, "none")
    assert body["consent_version"] == "2026-11"
    assert body["lingo"]["heading"] == "Non-verbal communication"


async def test_another_user_cannot_read(client, db_session, make_actor):
    await make_actor("nv-owner@example.com")
    other = await make_actor("nv-other@example.com")
    attempt_id = await _attempt(db_session, "nv-owner@example.com")
    response = await client.get(f"/api/v1/attempts/{attempt_id}/nonverbal", headers=bearer(other))
    assert response.status_code == 403
    assert response.json()["code"] == "attempt_not_yours"


async def test_batch_without_consent_is_refused(client, db_session, make_actor):
    token = await make_actor("nv-noconsent@example.com")
    attempt_id = await _attempt(db_session, "nv-noconsent@example.com")
    response = await client.post(
        f"/api/v1/attempts/{attempt_id}/nonverbal-batches", json=_batch(), headers=bearer(token)
    )
    assert response.status_code == 403
    assert response.json()["code"] == "nonverbal_consent_required"


async def test_consent_then_batch_is_pending_and_duplicate_seq_stores_one(client, db_session, make_actor):
    token = await make_actor("nv-flow@example.com")
    attempt_id = await _attempt(db_session, "nv-flow@example.com")
    assert (await _consent(client, token)).status_code == 200
    for _ in range(2):
        posted = await client.post(
            f"/api/v1/attempts/{attempt_id}/nonverbal-batches", json=_batch(0), headers=bearer(token)
        )
        assert posted.status_code == 202
    assert await _stored(db_session, attempt_id) == 1
    body = (await client.get(f"/api/v1/attempts/{attempt_id}/nonverbal", headers=bearer(token))).json()
    assert (body["consented"], body["state"]) == (True, "pending")


async def test_non_practice_attempt_is_not_available(client, db_session, make_actor):
    token = await make_actor("nv-slot@example.com")
    attempt_id = await _attempt(db_session, "nv-slot@example.com", kind="debrief")
    await _consent(client, token)
    read = await client.get(f"/api/v1/attempts/{attempt_id}/nonverbal", headers=bearer(token))
    assert read.json()["supported"] is False
    posted = await client.post(
        f"/api/v1/attempts/{attempt_id}/nonverbal-batches", json=_batch(), headers=bearer(token)
    )
    assert posted.status_code == 403
    assert posted.json()["code"] == "nonverbal_not_available"


async def test_org_self_practice_follows_the_organisation_switch(client, db_session, make_actor):
    token = await make_actor("nv-org@example.com")
    org = await tenancy_repo.create_organization(db_session, slug=f"nv-{uuid.uuid4().hex[:6]}", name="NV")
    attempt_id = await _attempt(db_session, "nv-org@example.com", kind="self_practice", org_id=org.id)
    off = await client.get(f"/api/v1/attempts/{attempt_id}/nonverbal", headers=bearer(token))
    assert off.json()["supported"] is False
    await db_session.execute(
        text("UPDATE organizations SET nonverbal_feedback_enabled = true WHERE id = :i"), {"i": org.id}
    )
    on = await client.get(f"/api/v1/attempts/{attempt_id}/nonverbal", headers=bearer(token))
    assert on.json()["supported"] is True


async def test_batch_after_the_interaction_is_complete_is_accepted_but_not_stored(
    client, db_session, make_actor
):
    token = await make_actor("nv-late@example.com")
    attempt_id = await _attempt(db_session, "nv-late@example.com")
    await _consent(client, token)
    await repository.set_status(
        db_session, attempt_id, status=domain.Status.INTERACTION_COMPLETE, at=datetime.now(UTC)
    )
    posted = await client.post(
        f"/api/v1/attempts/{attempt_id}/nonverbal-batches", json=_batch(), headers=bearer(token)
    )
    assert posted.status_code == 202
    assert await _stored(db_session, attempt_id) == 0


async def test_withdrawing_consent_deletes_batches_and_summaries(client, db_session, make_actor):
    token = await make_actor("nv-withdraw@example.com")
    attempt_id = await _attempt(db_session, "nv-withdraw@example.com")
    await _consent(client, token)
    await client.post(
        f"/api/v1/attempts/{attempt_id}/nonverbal-batches", json=_batch(), headers=bearer(token)
    )
    db_session.add(
        AttemptNonverbalSummary(
            attempt_id=attempt_id,
            state="insufficient",
            facts={},
            created_at=datetime.now(UTC) - timedelta(minutes=1),
        )
    )
    await db_session.flush()
    response = await _consent(client, token, consented=False)
    assert response.status_code == 200
    assert response.json()["consented"] is False
    assert await _stored(db_session, attempt_id) == 0
    summaries = await db_session.scalar(
        select(func.count())
        .select_from(AttemptNonverbalSummary)
        .where(AttemptNonverbalSummary.attempt_id == attempt_id)
    )
    assert summaries == 0


async def test_consent_with_a_stale_wording_version_is_refused_and_records_nothing(
    client, db_session, make_actor
):
    token = await make_actor("nv-stale@example.com")
    response = await client.put(
        "/api/v1/me/nonverbal-consent",
        json={"consented": True, "version": "2025-01"},
        headers=bearer(token),
    )
    assert (response.status_code, response.json()["code"]) == (422, "nonverbal_consent_version_stale")
    assert await db_session.scalar(text("SELECT count(*) FROM nonverbal_consents")) == 0
