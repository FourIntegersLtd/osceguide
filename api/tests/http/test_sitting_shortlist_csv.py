"""The shortlist CSV: decided candidates only, ranked, guarded against spreadsheet formulas."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from app.features.dashboard.schemas_report import CandidateReport
from app.features.dashboard.service_shortlist_csv import ranked_shortlist
from app.features.results.schemas import DecisionRead
from app.features.tenancy.models import AuditEntry
from tests.http.test_results_routes import org_with_admin, url
from tests.support.decisions import a_sitting_and_trainee
from tests.support.tokens import bearer


def _candidate(name: str, score: float | None, passed: int = 0) -> CandidateReport:
    return CandidateReport(
        user_id=uuid.uuid4(),
        trainee_id=uuid.uuid4(),
        name=name,
        email=f"{name}@example.com",
        stations_marked=1,
        overall_rag=None,
        score=score,
        stations_passed=passed,
        decision=None,
    )


def _decision(state: str = "signed_off", outcome: str | None = "pass") -> DecisionRead:
    return DecisionRead(
        revision=1,
        workflow_state=state,
        assessment_outcome=outcome,
        recruitment_outcome=None,
        rationale="ok",
        signed_off_at=datetime.now(UTC),
        released_at=None,
    )


def test_ranking_uses_the_rounded_score_shares_ties_and_leaves_unscored_last() -> None:
    a, b, c, d, e, f = (
        _candidate("a", 80.4, 3),
        _candidate("b", 79.6, 3),
        _candidate("c", 90.0),
        _candidate("d", 50.0),
        _candidate("e", None),
        _candidate("f", 95.0),
    )
    decisions = {x.trainee_id: _decision() for x in (a, b, c, d, e)}
    decisions[f.trainee_id] = _decision("draft")  # a draft is not a decision
    rows = ranked_shortlist([a, b, c, d, e, f], decisions)  # type: ignore[arg-type]
    assert [(rank, cand.name) for rank, cand, _ in rows] == [
        (1, "c"),
        (2, "a"),
        (2, "b"),
        (4, "d"),
        (None, "e"),
    ]


def test_a_withheld_outcome_is_not_shortlisted() -> None:
    a = _candidate("a", 70.0)
    assert ranked_shortlist([a], {a.trainee_id: _decision(outcome="withheld")}) == []  # type: ignore[dict-item]


pytestmark = pytest.mark.db


async def test_only_decided_candidates_are_exported_with_a_quoted_reason_and_an_audit_row(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting, signed = await a_sitting_and_trainee(db_session, org_id)
    from app.features.roster.models import Trainee
    from app.features.sittings.models import Sitting
    from tests.support.decisions import seat_candidate

    other = Trainee(org_id=org_id, email="draft-one@example.com")
    db_session.add(other)
    await db_session.flush()
    await seat_candidate(db_session, org_id, sitting, other.id)
    assert await db_session.get(Sitting, sitting) is not None
    for trainee, reason in ((signed, "=HYPERLINK(1)"), (other.id, "Still thinking")):
        saved = await client.put(
            url(sitting, trainee),
            json={"assessment_outcome": "pass", "rationale": reason},
            headers=bearer(admin),
        )
        assert saved.status_code == 200, saved.text
    assert (await client.post(url(sitting, signed, "/sign-off"), headers=bearer(admin))).status_code == 200

    exported = await client.get(f"/api/v1/orgs/kings/sittings/{sitting}/shortlist.csv", headers=bearer(admin))
    assert exported.status_code == 200, exported.text
    assert exported.headers["content-disposition"] == 'attachment; filename="finals-shortlist.csv"'
    lines = exported.content.decode("utf-8").split("\n")
    assert lines[0] == "﻿rank,name,email,score,outcome,reason"
    assert len([line for line in lines[1:] if line]) == 1
    assert lines[1].endswith(",pass,'=HYPERLINK(1)")

    audit = (
        (
            await db_session.execute(
                select(AuditEntry).where(
                    AuditEntry.org_id == org_id, AuditEntry.action == "results.shortlist_exported"
                )
            )
        )
        .scalars()
        .all()
    )
    assert [entry.target_id for entry in audit] == [str(sitting)]

    supervisor = await make_actor(
        "sup-short@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="supervisor"),),
        active_org_slug="kings",
    )
    refused = await client.get(
        f"/api/v1/orgs/kings/sittings/{sitting}/shortlist.csv", headers=bearer(supervisor)
    )
    assert refused.status_code == 403
