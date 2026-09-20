"""The trigger that makes a decision defensible."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.results import domain, repository
from tests.support.rubrics import published_feedback_version

pytestmark = pytest.mark.db


async def a_revision(db_session: AsyncSession) -> uuid.UUID:
    from app.features.roster.models import Trainee
    from app.features.sittings.models import Sitting
    from app.features.tenancy import repository as tenancy_repo

    org = await tenancy_repo.create_organization(db_session, slug="ao", name="AO")
    version = await published_feedback_version(db_session, org.id)
    await db_session.flush()
    sitting = Sitting(org_id=org.id, name="S", mode="exam", rubric_version_id=version.id)
    trainee = Trainee(org_id=org.id, email="ao@example.com")
    db_session.add_all([sitting, trainee])
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
        rationale="Met the standard.",
        moderation_notes=None,
        evidence_snapshot={"x": 1},
        evidence_fingerprint=domain.fingerprint({"x": 1}),
        created_by=None,
    )
    return row.id


async def test_a_revision_cannot_be_updated(db_session: AsyncSession) -> None:
    """Not a convention — the database refuses.

    A candidate's outcome has to be defensible months later, so a correction is
    a new revision rather than a quiet edit of the old one.
    """
    revision_id = await a_revision(db_session)
    with pytest.raises(Exception, match="append-only"):
        await db_session.execute(
            text("update candidate_result_revisions set rationale = 'changed' where id = :i"),
            {"i": revision_id},
        )


async def test_a_revision_cannot_be_deleted(db_session: AsyncSession) -> None:
    revision_id = await a_revision(db_session)
    with pytest.raises(Exception, match="append-only"):
        await db_session.execute(
            text("delete from candidate_result_revisions where id = :i"), {"i": revision_id}
        )
