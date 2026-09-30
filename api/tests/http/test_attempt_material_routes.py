"""What a candidate may read about a station they are sitting, or have sat.

The rule under test is a disclosure rule, so the refusals matter as much as the
answers: the brief is readable from the moment the attempt exists, the model
answer only once the consultation is over, and neither of them by anybody else.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import domain
from app.features.attempts import repository as attempts_repo
from app.features.entitlements import repository as ent_repo
from app.features.identity import repository as identity_repo
from app.features.stations import repository as stations_repo
from app.features.stations import repository_templates as templates_repo
from tests.support.catalog import ensure_exam
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

NOW = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)

# A station shaped like the documents the consumer library actually holds: a
# nested patient block the candidate must never see, a doctor block they read
# before the consultation, and a plan they read after it. `hidden_extra` and
# `key_concerns` stand in for the keys an exam adds that these schemas do not
# name — one must survive the passthrough and the other must not leak.
STATION_CONTENT = {
    "station_name": "Chest pain",
    "doctor_information": {
        "patient_biodata": "Mr Ade Bello, 54",
        "recent_notes": ["Seen last week"],
        "current_medications": ["Ramipril"],
        "past_medical_history": ["Hypertension"],
        "social_history": ["Smokes 10/day"],
        "recent_investigations": ["ECG normal"],
        "photos": ["https://cdn.example.com/ecg.png"],
        "task_instructions": "Take a history.",
    },
    "patient_information": {
        "patient_biodata": "Mr Ade Bello, 54",
        "gender": "male",
        "idea": ["Thinks it is indigestion"],
        "concerns": ["Worried about his heart"],
        "expectation": ["Wants a scan"],
        "persona": "Anxious, talks quickly",
        "opening_sentence": "Doctor, I have this pain.",
        "expanded_history": "Crushing central chest pain for three days.",
    },
    "management_plan": {
        "explanation": "Likely stable angina.",
        "differential_diagnosis": ["ACS", "GORD"],
        "immediate_actions": ["ECG", "Troponin"],
        "safety_netting": "Return if pain at rest.",
    },
    "key_concerns": ["Missed ACS"],
}

# The template these tests bind every station to. Section ids match
# `STATION_CONTENT`'s nested keys, so `domain_content.content_for_template`
# lifts each nested block onto its own id the same way a platform-authored
# template's does; block ids are a block's own id within that nested dict.
# `escalation` names no schema anywhere — it is declared here and nowhere
# else, which is the point of `test_a_station_key_no_schema_names_still_reaches_the_client`.
TEMPLATE_STRUCTURE = {
    "schemaVersion": 1,
    "sections": [
        {
            "id": "doctor_information",
            "title": "Doctor information",
            "audience": "candidate",
            "blocks": [
                {"id": "patient_biodata", "type": "text", "label": "Patient", "role": "candidate_brief"},
                {"id": "recent_notes", "type": "list", "label": "Notes", "role": "candidate_brief"},
                {
                    "id": "current_medications",
                    "type": "list",
                    "label": "Medications",
                    "role": "candidate_brief",
                },
                {"id": "past_medical_history", "type": "list", "label": "History", "role": "candidate_brief"},
                {
                    "id": "social_history",
                    "type": "list",
                    "label": "Social history",
                    "role": "candidate_brief",
                },
                {
                    "id": "recent_investigations",
                    "type": "list",
                    "label": "Investigations",
                    "role": "candidate_brief",
                },
                {"id": "photos", "type": "list", "label": "Photos", "role": "candidate_brief"},
                {"id": "task_instructions", "type": "text", "label": "Task", "role": "candidate_brief"},
            ],
        },
        {
            "id": "patient_information",
            "title": "Patient information",
            "audience": "patient",
            "blocks": [
                {"id": "patient_biodata", "type": "text", "label": "Patient", "role": "persona"},
                {"id": "gender", "type": "text", "label": "Gender", "role": "persona"},
                {"id": "idea", "type": "list", "label": "Idea", "role": "hidden"},
                {"id": "concerns", "type": "list", "label": "Concerns", "role": "hidden"},
                {"id": "expectation", "type": "list", "label": "Expectation", "role": "hidden"},
                {"id": "persona", "type": "text", "label": "Persona", "role": "hidden"},
                {"id": "opening_sentence", "type": "text", "label": "Opens with", "role": "hidden"},
                {"id": "expanded_history", "type": "text", "label": "History", "role": "hidden"},
            ],
        },
        {
            "id": "management_plan",
            "title": "Management plan",
            "audience": "examiner",
            "blocks": [
                {"id": "explanation", "type": "text", "label": "Explanation", "role": "examiner"},
                {
                    "id": "differential_diagnosis",
                    "type": "list",
                    "label": "Differentials",
                    "role": "examiner",
                },
                {"id": "immediate_actions", "type": "list", "label": "Immediate actions", "role": "examiner"},
                {"id": "safety_netting", "type": "text", "label": "Safety netting", "role": "examiner"},
                {"id": "escalation", "type": "text", "label": "Escalation", "role": "examiner"},
            ],
        },
    ],
    "layout": {"persona": "patient"},
}


@dataclass(frozen=True)
class Sat:
    """The ids a test needs, read while the rows are still attached.

    Plain values rather than the ORM rows: `commit()` expires every attribute,
    and reading one back outside a greenlet raises `MissingGreenlet` rather
    than quietly issuing a query.
    """

    user_id: uuid.UUID
    station_id: uuid.UUID
    version_id: uuid.UUID
    attempt_id: uuid.UUID


async def _template_version(session: AsyncSession, exam_id: uuid.UUID) -> uuid.UUID:
    """A published template with `TEMPLATE_STRUCTURE`, one per test's exam."""
    template = await templates_repo.create_template(session, None, exam_id=exam_id, title="Consultation")
    version = await templates_repo.add_template_version(
        session, None, template_id=template.id, version=1, structure=TEMPLATE_STRUCTURE
    )
    await templates_repo.set_template_version_status(
        session, None, version.id, status="published", at=NOW, by=None
    )
    await session.flush()
    return version.id


async def _station(
    session: AsyncSession, exam_id: uuid.UUID, content: dict | None = None
) -> tuple[uuid.UUID, uuid.UUID]:
    """A published platform-library station bound to `TEMPLATE_STRUCTURE`, which is what a consumer sits."""
    template_version_id = await _template_version(session, exam_id)
    station = await stations_repo.create_station(session, None, exam_id=exam_id, title="Chest pain")
    version = await stations_repo.add_version(
        session,
        None,
        station_id=station.id,
        version=1,
        content=content or STATION_CONTENT,
        template_version_id=template_version_id,
    )
    await stations_repo.set_version_status(session, None, version.id, status="published", at=NOW, by=None)
    await session.flush()
    return station.id, version.id


async def _entitled_attempt(session: AsyncSession, email: str, *, content: dict | None = None) -> Sat:
    exam = await ensure_exam(session, "sca")
    assert exam is not None
    user = await identity_repo.user_by_email(session, email)
    assert user is not None
    await ent_repo.grant(
        session,
        user_id=user.id,
        exam_id=exam.id,
        source="purchase",
        ends_at=datetime.now(UTC) + timedelta(days=30),
    )
    station_id, version_id = await _station(session, exam.id, content)
    attempt = await attempts_repo.create_attempt(
        session,
        kind="practice",
        user_id=user.id,
        exam_id=exam.id,
        org_id=None,
        station_version_id=version_id,
    )
    sat = Sat(user_id=user.id, station_id=station_id, version_id=version_id, attempt_id=attempt.id)
    await session.commit()
    return sat


async def test_the_brief_is_readable_as_soon_as_the_attempt_exists(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """The reading period is the first thing that happens, so `created` is enough."""
    token = await make_actor("brief@example.com")
    sat = await _entitled_attempt(db_session, "brief@example.com")

    response = await client.get(f"/api/v1/attempts/{sat.attempt_id}/brief", headers=bearer(token))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "created"
    assert body["station_title"] == "Chest pain"
    assert body["station_id"] == str(sat.station_id)
    assert body["station_version_id"] == str(sat.version_id)
    assert body["exam_code"] == "sca"
    doctor_section = next(s for s in body["sections"] if s["id"] == "doctor_information")
    blocks = {block["id"]: block["value"] for block in doctor_section["blocks"]}
    assert blocks["patient_biodata"] == "Mr Ade Bello, 54"
    assert blocks["photos"] == ["https://cdn.example.com/ecg.png"]
    assert body["patient"]["gender"] == "male"


async def test_the_brief_never_carries_the_patient_or_the_plan(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """Reading the brief must not be a way to read the answers.

    The whole reason this route exists rather than putting `content` on the
    library read: the patient's persona and the management plan are what the
    station assesses.
    """
    token = await make_actor("leak@example.com")
    sat = await _entitled_attempt(db_session, "leak@example.com")

    body = (await client.get(f"/api/v1/attempts/{sat.attempt_id}/brief", headers=bearer(token))).json()

    section_ids = {section["id"] for section in body["sections"]}
    assert section_ids == {"doctor_information"}
    serialised = str(body)
    assert "Anxious, talks quickly" not in serialised
    assert "Likely stable angina" not in serialised
    assert "Crushing central chest pain" not in serialised


async def test_the_review_is_refused_until_the_consultation_is_over(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("early@example.com")
    sat = await _entitled_attempt(db_session, "early@example.com")

    refused = await client.get(f"/api/v1/attempts/{sat.attempt_id}/review", headers=bearer(token))
    assert refused.status_code == 409
    assert refused.json()["code"] == "attempt_not_finished"

    await attempts_repo.set_status(db_session, sat.attempt_id, status=domain.Status.RUNNING, at=NOW)
    await db_session.commit()
    still_refused = await client.get(f"/api/v1/attempts/{sat.attempt_id}/review", headers=bearer(token))
    assert still_refused.status_code == 409


async def test_the_review_is_the_model_answer_once_the_interaction_is_complete(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("review@example.com")
    sat = await _entitled_attempt(db_session, "review@example.com")
    await attempts_repo.set_status(db_session, sat.attempt_id, status=domain.Status.RUNNING, at=NOW)
    await attempts_repo.set_status(
        db_session, sat.attempt_id, status=domain.Status.INTERACTION_COMPLETE, at=NOW
    )
    await db_session.commit()

    response = await client.get(f"/api/v1/attempts/{sat.attempt_id}/review", headers=bearer(token))

    assert response.status_code == 200, response.text
    body = response.json()
    section_ids = {section["id"] for section in body["sections"]}
    # Candidate again, plus every examiner section — the model answer and the
    # marking guidance. Not the patient audience: how the patient is played
    # stays on the server even after the consultation, readable only through
    # `/attempts/{id}/roleplay` by the candidate who is about to play it back.
    assert section_ids == {"doctor_information", "management_plan"}
    plan = next(s for s in body["sections"] if s["id"] == "management_plan")
    blocks = {block["id"]: block["value"] for block in plan["blocks"]}
    assert blocks["explanation"] == "Likely stable angina."
    assert blocks["immediate_actions"] == ["ECG", "Troponin"]


async def test_a_station_key_no_schema_names_still_reaches_the_client(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """Four exams' documents differ, and the fifth is not written yet.

    The blocks are passthrough so a station carrying more than these schemas
    name renders rather than silently losing half of itself.
    """
    token = await make_actor("extra@example.com")
    content = dict(STATION_CONTENT)
    content["management_plan"] = {**STATION_CONTENT["management_plan"], "escalation": "Refer same day"}
    sat = await _entitled_attempt(db_session, "extra@example.com", content=content)
    await attempts_repo.set_status(db_session, sat.attempt_id, status=domain.Status.RUNNING, at=NOW)
    await attempts_repo.set_status(
        db_session, sat.attempt_id, status=domain.Status.INTERACTION_COMPLETE, at=NOW
    )
    await db_session.commit()

    body = (await client.get(f"/api/v1/attempts/{sat.attempt_id}/review", headers=bearer(token))).json()

    plan = next(s for s in body["sections"] if s["id"] == "management_plan")
    blocks = {block["id"]: block["value"] for block in plan["blocks"]}
    assert blocks["escalation"] == "Refer same day"


async def test_an_abandoned_attempt_is_still_reviewable(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """Somebody who walked out still sat the station and may read what they missed."""
    token = await make_actor("gone@example.com")
    sat = await _entitled_attempt(db_session, "gone@example.com")
    await attempts_repo.set_status(db_session, sat.attempt_id, status=domain.Status.FAILED, at=NOW)
    await db_session.commit()

    response = await client.get(f"/api/v1/attempts/{sat.attempt_id}/review", headers=bearer(token))

    assert response.status_code == 200, response.text


async def test_neither_read_is_available_to_anybody_else(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    await make_actor("owner2@example.com")
    sat = await _entitled_attempt(db_session, "owner2@example.com")
    intruder = await make_actor("intruder@example.com")

    for path in ("brief", "review"):
        response = await client.get(f"/api/v1/attempts/{sat.attempt_id}/{path}", headers=bearer(intruder))
        assert response.status_code == 403, path
        assert response.json()["code"] == "attempt_not_yours"


async def test_my_attempts_lists_what_i_have_sat_newest_first(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("history@example.com")
    first = await _entitled_attempt(db_session, "history@example.com")
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    second = await attempts_repo.create_attempt(
        db_session,
        kind="practice",
        user_id=first.user_id,
        exam_id=exam.id,
        org_id=None,
        station_version_id=first.version_id,
    )
    second_id = second.id
    await db_session.commit()

    response = await client.get("/api/v1/me/attempts", headers=bearer(token))

    assert response.status_code == 200, response.text
    items = response.json()["items"]
    # Both, and only these two. The order within one instant is the id's to
    # decide — rows written in one transaction share a `now()`, which is the
    # tie `keyset_page` breaks on purpose.
    assert {item["id"] for item in items} == {str(second_id), str(first.attempt_id)}
    assert items[0]["station_title"] == "Chest pain"
    assert items[0]["station_id"] == str(first.station_id)
    assert items[0]["exam_code"] == "sca"
    assert items[0]["has_result"] is False


async def test_my_attempts_can_be_narrowed_to_one_station(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """ "Every time I have sat this one" is what the transcript picker asks."""
    token = await make_actor("narrow@example.com")
    mine = await _entitled_attempt(db_session, "narrow@example.com")
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    _, other_version_id = await _station(db_session, exam.id, {"station_name": "Other"})
    await attempts_repo.create_attempt(
        db_session,
        kind="practice",
        user_id=mine.user_id,
        exam_id=exam.id,
        org_id=None,
        station_version_id=other_version_id,
    )
    await db_session.commit()

    response = await client.get(
        f"/api/v1/me/attempts?station_version_id={mine.version_id}", headers=bearer(token)
    )

    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert [item["id"] for item in items] == [str(mine.attempt_id)]


async def test_my_attempts_search_matches_exam_code_or_kind_label(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """The same two fields `TranscriptList` filtered client-side: the exam's
    code, and the kind spelled the way the transcripts table renders it."""
    token = await make_actor("search-attempts@example.com")
    sca_attempt = await _entitled_attempt(db_session, "search-attempts@example.com")
    plab_exam = await ensure_exam(db_session, "plab")
    await attempts_repo.create_attempt(
        db_session,
        kind="practice",
        user_id=sca_attempt.user_id,
        exam_id=plab_exam.id,
        org_id=None,
    )
    await db_session.commit()

    by_exam_code = await client.get("/api/v1/me/attempts", params={"search": "plab"}, headers=bearer(token))
    by_kind_label = await client.get(
        "/api/v1/me/attempts", params={"search": "Practice"}, headers=bearer(token)
    )

    assert by_exam_code.status_code == 200, by_exam_code.text
    assert [item["exam_code"] for item in by_exam_code.json()["items"]] == ["plab"]
    # Both attempts are `practice`, so both match the kind label.
    assert {item["exam_code"] for item in by_kind_label.json()["items"]} == {"sca", "plab"}


async def test_my_attempts_transcribable_only_drops_an_attempt_that_never_started(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """`listTranscribableAttempts` dropped anything still `created`: it never
    reached the room, so there is nothing to transcribe yet."""
    token = await make_actor("transcribable@example.com")
    never_started = await _entitled_attempt(db_session, "transcribable@example.com")
    ran = await attempts_repo.create_attempt(
        db_session,
        kind="practice",
        user_id=never_started.user_id,
        exam_id=(await ensure_exam(db_session, "sca")).id,
        org_id=None,
    )
    ran_id = ran.id
    await attempts_repo.set_status(db_session, ran_id, status=domain.Status.RUNNING, at=NOW)
    await db_session.commit()

    response = await client.get(
        "/api/v1/me/attempts", params={"transcribable_only": True}, headers=bearer(token)
    )

    assert response.status_code == 200, response.text
    assert [item["id"] for item in response.json()["items"]] == [str(ran_id)]


async def test_my_attempts_shows_nobody_elses(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    await make_actor("theirs@example.com")
    await _entitled_attempt(db_session, "theirs@example.com")
    stranger = await make_actor("stranger@example.com")

    response = await client.get("/api/v1/me/attempts", headers=bearer(stranger))

    assert response.status_code == 200
    assert response.json()["items"] == []
