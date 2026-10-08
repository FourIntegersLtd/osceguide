"""Downloading a sitting's results, and one candidate's released result."""

from __future__ import annotations

import uuid
from io import BytesIO

import pytest
from httpx import AsyncClient
from pypdf import PdfReader
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from app.features.sittings.models import Slot
from app.features.tenancy.models import AuditEntry
from tests.http.test_org_read_models import a_circuit, a_sitting
from tests.http.test_results_routes import a_sitting_and_trainee, org_with_admin, url
from tests.http.test_sittings_routes import published_station
from tests.support.decisions import seat_candidate
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def test_the_csv_is_the_report_with_a_formula_name_quoted(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings", mode="exam")
    station = await published_station(client, admin, "kings", "Chest pain")
    rostered = await client.post(
        "/api/v1/orgs/kings/trainees",
        json={"email": "equals@example.com", "first_name": "=Ada"},
        headers=bearer(admin),
    )
    assert rostered.status_code == 201, rostered.text
    trainee_id = rostered.json()["id"]
    user_id = rostered.json()["user_id"]
    await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[user_id],
        station_version_ids=[station],
    )

    exported = await client.get(
        f"/api/v1/orgs/kings/sittings/{sitting['id']}/report.csv", headers=bearer(admin)
    )
    assert exported.status_code == 200, exported.text
    assert exported.headers["content-type"].startswith("text/csv")
    assert exported.headers["content-disposition"] == 'attachment; filename="finals-results.csv"'
    assert exported.text == (
        "\ufeff"
        "name,email,user_id,trainee_id,stations,stations_marked,overall_rag,score,stations_passed,"
        "decision_workflow_state,decision_assessment_outcome,decision_recruitment_outcome,"
        "decision_signed_off_at,decision_released_at\n"
        f"'=Ada,equals@example.com,{user_id},{trainee_id},1,0,,,0,,,,,\n"
    )

    entries = (
        (
            await db_session.execute(
                select(AuditEntry).where(
                    AuditEntry.org_id == org_id,
                    AuditEntry.action == "results.exported",
                    AuditEntry.target_type == "sitting",
                )
            )
        )
        .scalars()
        .all()
    )
    assert [entry.target_id for entry in entries] == [sitting["id"]]

    supervisor = await make_actor(
        "sup-csv@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="supervisor"),),
        active_org_slug="kings",
    )
    refused = await client.get(
        f"/api/v1/orgs/kings/sittings/{sitting['id']}/report.csv", headers=bearer(supervisor)
    )
    assert refused.status_code == 403
    assert refused.json()["code"] == "forbidden"


async def _draft(client: AsyncClient, make_actor, db_session: AsyncSession, email: str):  # type: ignore[no-untyped-def]
    """A signed-in candidate with a draft decision. The failing read has to be last."""
    from app.features.identity import repository as identity_repo
    from app.features.roster import repository as roster_repo

    org_id, admin = await org_with_admin(client, make_actor)
    sitting, trainee = await a_sitting_and_trainee(db_session, org_id)
    candidate = await make_actor(email)
    user = await identity_repo.user_by_email(db_session, email)
    assert user is not None
    await roster_repo.link_trainee_to_user(db_session, org_id, trainee, user_id=user.id)
    await db_session.flush()
    await seat_candidate(db_session, org_id, sitting, trainee)
    saved = await client.put(
        url(sitting, trainee),
        json={"assessment_outcome": "pass", "rationale": "Draft."},
        headers=bearer(admin),
    )
    assert saved.status_code == 200, saved.text
    return sitting, trainee, admin, candidate


async def test_an_unreleased_result_pdf_is_refused_to_the_admin(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    sitting, trainee, admin, _candidate = await _draft(
        client, make_actor, db_session, "draft-admin@example.com"
    )
    response = await client.get(
        f"/api/v1/orgs/kings/sittings/{sitting}/candidates/{trainee}/result.pdf",
        headers=bearer(admin),
    )
    assert response.status_code == 404, response.text
    assert response.json()["code"] == "result_not_released"


async def test_an_unreleased_result_pdf_is_refused_to_the_candidate(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    sitting, _trainee, _admin, candidate = await _draft(
        client, make_actor, db_session, "draft-candidate@example.com"
    )
    response = await client.get(f"/api/v1/me/results/{sitting}.pdf", headers=bearer(candidate))
    assert response.status_code == 404, response.text
    assert response.json()["code"] == "result_not_released"


async def test_a_released_result_pdf_names_the_candidate_and_another_org_is_refused(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting, trainee = await a_sitting_and_trainee(db_session, org_id)
    candidate = await make_actor("lukasz@example.com")
    from app.features.identity import repository as identity_repo
    from app.features.roster import repository as roster_repo

    user = await identity_repo.user_by_email(db_session, "lukasz@example.com")
    assert user is not None
    user.name = "Łukasz Żółć"
    await roster_repo.link_trainee_to_user(db_session, org_id, trainee, user_id=user.id)
    await db_session.flush()
    await seat_candidate(db_session, org_id, sitting, trainee)
    await client.put(
        url(sitting, trainee),
        json={
            "assessment_outcome": "pass",
            "rationale": "Safe and thorough",
            "moderation_notes": "SECRET-MODERATION",
        },
        headers=bearer(admin),
    )
    await client.post(url(sitting, trainee, "/sign-off"), headers=bearer(admin))
    released = await client.post(url(sitting, trainee, "/release"), headers=bearer(admin))
    assert released.status_code == 200, released.text

    admin_pdf = await client.get(
        f"/api/v1/orgs/kings/sittings/{sitting}/candidates/{trainee}/result.pdf",
        headers=bearer(admin),
    )
    mine = await client.get(f"/api/v1/me/results/{sitting}.pdf", headers=bearer(candidate))
    assert admin_pdf.status_code == 200, admin_pdf.content[:200]
    assert mine.status_code == 200, mine.content[:200]
    assert admin_pdf.headers["content-disposition"] == 'attachment; filename="finals-ukasz-result.pdf"'
    assert mine.headers["content-disposition"] == 'attachment; filename="finals-result.pdf"'

    assert admin_pdf.content.startswith(b"%PDF-")
    assert mine.content.startswith(b"%PDF-")
    reader = PdfReader(BytesIO(admin_pdf.content))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "Assessment result" in text
    assert "Łukasz Żółć" in text
    assert "Outcome Pass" in text
    assert "Safe and thorough" in text
    assert "SECRET-MODERATION" not in text
    assert "Sitting:" not in text

    entries = (
        (
            await db_session.execute(
                select(AuditEntry).where(
                    AuditEntry.org_id == org_id,
                    AuditEntry.action == "results.exported",
                    AuditEntry.target_type == "trainee",
                )
            )
        )
        .scalars()
        .all()
    )
    assert [entry.target_id for entry in entries] == [str(trainee)]

    _, other = await org_with_admin(client, make_actor, slug="guys")
    refused = await client.get(
        f"/api/v1/orgs/kings/sittings/{sitting}/candidates/{trainee}/result.pdf",
        headers=bearer(other),
    )
    assert refused.status_code == 403
    assert refused.json()["code"] == "forbidden"


async def test_a_released_decision_is_a_row_of_the_csv(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    _org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings", mode="exam")
    station = await published_station(client, admin, "kings", "Chest pain")
    rostered = await client.post(
        "/api/v1/orgs/kings/trainees",
        json={"email": "released-csv@example.com", "first_name": "Ada"},
        headers=bearer(admin),
    )
    assert rostered.status_code == 201, rostered.text
    trainee_id = rostered.json()["id"]
    user_id = rostered.json()["user_id"]
    await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[user_id],
        station_version_ids=[station],
    )
    # Ada sat her one station (R-11): only a candidate who sat is decided on.
    await db_session.execute(
        update(Slot).where(Slot.trainee_id == uuid.UUID(user_id)).values(status="completed")
    )
    saved = await client.put(
        url(sitting["id"], trainee_id),
        json={"assessment_outcome": "pass", "rationale": "Met the standard."},
        headers=bearer(admin),
    )
    assert saved.status_code == 200, saved.text
    signed = await client.post(
        url(sitting["id"], trainee_id, "/sign-off"),
        headers=bearer(admin),
    )
    assert signed.status_code == 200, signed.text
    released = await client.post(
        url(sitting["id"], trainee_id, "/release"),
        headers=bearer(admin),
    )
    assert released.status_code == 200, released.text

    exported = await client.get(
        f"/api/v1/orgs/kings/sittings/{sitting['id']}/report.csv", headers=bearer(admin)
    )
    assert exported.status_code == 200, exported.text
    header, row = exported.text.splitlines()
    assert header == (
        "\ufeff"
        "name,email,user_id,trainee_id,stations,stations_marked,overall_rag,score,stations_passed,"
        "decision_workflow_state,decision_assessment_outcome,decision_recruitment_outcome,"
        "decision_signed_off_at,decision_released_at"
    )
    assert row.startswith(f"Ada,released-csv@example.com,{user_id},{trainee_id},1,0,,,0,released,pass,")


async def test_an_anonymised_candidates_pdf_does_not_name_them(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """S-21: the account still holds the real name; the document must not print it."""
    org_id, admin = await org_with_admin(client, make_actor)
    sitting, trainee = await a_sitting_and_trainee(db_session, org_id)
    await make_actor("lukasz@example.com")
    from app.features.identity import repository as identity_repo
    from app.features.roster import repository as roster_repo

    user = await identity_repo.user_by_email(db_session, "lukasz@example.com")
    assert user is not None
    user.name = "Łukasz Żółć"
    await roster_repo.link_trainee_to_user(db_session, org_id, trainee, user_id=user.id)
    await db_session.flush()
    await seat_candidate(db_session, org_id, sitting, trainee)
    await client.put(
        url(sitting, trainee),
        json={"assessment_outcome": "pass", "rationale": "Safe", "moderation_notes": "n"},
        headers=bearer(admin),
    )
    await client.post(url(sitting, trainee, "/sign-off"), headers=bearer(admin))
    assert (await client.post(url(sitting, trainee, "/release"), headers=bearer(admin))).status_code == 200
    gone = await client.post(f"/api/v1/orgs/kings/trainees/{trainee}/anonymise", headers=bearer(admin))
    assert gone.status_code == 200, gone.text

    pdf = await client.get(
        f"/api/v1/orgs/kings/sittings/{sitting}/candidates/{trainee}/result.pdf", headers=bearer(admin)
    )
    assert pdf.status_code == 200, pdf.content[:200]
    text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf.content)).pages)
    assert "Anonymised trainee" in text
    assert "Łukasz" not in text
    assert "ukasz" not in pdf.headers["content-disposition"]
