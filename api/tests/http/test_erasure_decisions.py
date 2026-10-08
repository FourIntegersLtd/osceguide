"""S-20: erasing a person scrubs what was written about them in a decision, and keeps the decision."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.identity.service_erasure import erase_due_accounts
from app.features.results import domain, repository
from tests.http.test_identity_routes import _closed_long_ago, opener
from tests.support.rubrics import published_feedback_version

pytestmark = pytest.mark.db


async def test_erasure_replaces_decision_text_and_keeps_the_decision(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.features.roster import repository as roster_repo
    from app.features.sittings.models import Sitting
    from app.features.tenancy import repository as tenancy_repo

    user_id = await _closed_long_ago(client, db_session, "decided@example.com")
    org = await tenancy_repo.create_organization(db_session, slug="er3-org", name="ER3")
    version = await published_feedback_version(db_session, org.id)
    trainee = await roster_repo.create_trainee(
        db_session, org.id, email="decided@example.com", first_name="D", last_name="P", cohort_id=None
    )
    trainee.user_id = user_id
    sitting = Sitting(org_id=org.id, name="S", mode="exam", rubric_version_id=version.id)
    db_session.add(sitting)
    await db_session.flush()
    row = await repository.append_revision(
        db_session,
        org.id,
        sitting_id=sitting.id,
        trainee_id=trainee.id,
        revision=1,
        supersedes_revision=None,
        workflow_state="draft",
        assessment_outcome="pass",
        recruitment_outcome=None,
        rationale="D P was nervous but safe.",
        moderation_notes="Second marker doubts D P.",
        evidence_snapshot={"x": 1},
        evidence_fingerprint=domain.fingerprint({"x": 1}),
        created_by=None,
    )
    await db_session.commit()

    assert await erase_due_accounts(opener(db_session), now=datetime.now(UTC)) == 1

    got = (
        await db_session.execute(
            text(
                "select rationale, moderation_notes, assessment_outcome, workflow_state, created_at "
                "from candidate_result_revisions where id = :i"
            ),
            {"i": row.id},
        )
    ).one()
    assert (got.rationale, got.moderation_notes) == ("[erased]", "[erased]")
    assert (got.assessment_outcome, got.workflow_state) == ("pass", "draft")
    assert got.created_at == row.created_at


async def test_the_trigger_still_refuses_any_other_edit(db_session: AsyncSession) -> None:
    from tests.repository.test_results_append_only import a_revision

    revision_id = await a_revision(db_session)
    with pytest.raises(Exception, match="append-only"):
        await db_session.execute(
            text(
                "update candidate_result_revisions set assessment_outcome = 'fail', rationale = '[erased]' "
                "where id = :i"
            ),
            {"i": revision_id},
        )
