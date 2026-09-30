"""The spreadsheet and the PDF, without a database: the bytes themselves."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from io import BytesIO

from pypdf import PdfReader

from app.features.dashboard.schemas_org import ConsoleSitting
from app.features.dashboard.schemas_report import (
    CandidateReport,
    DecisionSummary,
    ReportTotals,
    SittingReport,
)
from app.features.dashboard.service_report_csv import render_sitting_results_csv
from app.features.results.schemas import TraineeResultRead
from app.features.results.service_result_pdf import download_filename, render_result_pdf

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
SITTING_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


def test_a_formula_name_is_quoted_and_the_csv_is_exact() -> None:
    report = SittingReport(
        sitting=ConsoleSitting(
            id=SITTING_ID,
            name="Finals",
            mode="exam",
            sitting_type="exam",
            status="scheduled",
            scheduled_for=None,
            rubric_version_id=USER_ID,
        ),
        totals=ReportTotals(candidates=1, stations=0, stations_marked=0, decisions_released=1),
        candidates=[
            CandidateReport(
                user_id=USER_ID,
                trainee_id=None,
                name="=cmd",
                email="a@example.com",
                stations=[],
                stations_marked=0,
                overall_rag=None,
                decision=DecisionSummary(
                    workflow_state="released",
                    assessment_outcome="pass",
                    recruitment_outcome=None,
                    signed_off_at=datetime(2026, 9, 1, 12, 0, tzinfo=UTC),
                    released_at=datetime(2026, 9, 2, 12, 0, tzinfo=UTC),
                ),
            )
        ],
    )

    text = render_sitting_results_csv(report).decode("utf-8")
    assert text == (
        "\ufeff"
        "name,email,user_id,trainee_id,stations,stations_marked,overall_rag,score,stations_passed,"
        "decision_workflow_state,decision_assessment_outcome,decision_recruitment_outcome,"
        "decision_signed_off_at,decision_released_at\n"
        "'=cmd,a@example.com,11111111-1111-1111-1111-111111111111,,0,0,,,0,released,pass,,"
        "2026-09-01T12:00:00+00:00,2026-09-02T12:00:00+00:00\n"
    )


def test_the_pdf_names_a_candidate_beyond_latin_1_and_their_outcome() -> None:
    payload = render_result_pdf(
        organisation_name="Kings",
        sitting_name="Finals",
        sitting_date=datetime(2026, 9, 1, 9, 0, tzinfo=UTC),
        candidate_name="Łukasz Żółć",
        result=TraineeResultRead(
            sitting_id=SITTING_ID,
            assessment_outcome="pass",
            rationale="Safe and thorough",
            released_at=datetime(2026, 9, 2, 12, 0, tzinfo=UTC),
            assessment_score=None,
            acknowledged_at=None,
        ),
        generated_at=datetime(2026, 9, 3, 8, 0, tzinfo=UTC),
    )

    assert payload.startswith(b"%PDF-")
    reader = PdfReader(BytesIO(payload))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert text == (
        "Assessment result\n"
        "Kings\n"
        "Finals\n"
        "Candidate Łukasz Żółć\n"
        "Date of sitting 1 September 2026\n"
        "Outcome Pass\n"
        "Score Not recorded\n"
        "Released 2 September 2026, 12:00 UTC\n"
        "Rationale\n"
        "Safe and thorough\n"
        "Generated 3 September 2026, 08:00 UTC"
    )


def test_an_admin_filename_names_the_candidate_and_falls_back_to_the_trainee_id() -> None:
    trainee = uuid.UUID("33333333-3333-3333-3333-333333333333")
    assert (
        download_filename("Finals", SITTING_ID, candidate_name="Łukasz Żółć", trainee_id=trainee)
        == "finals-ukasz-result.pdf"
    )
    assert (
        download_filename("Finals", SITTING_ID, candidate_name="Żółć", trainee_id=trainee)
        == f"finals-{trainee}-result.pdf"
    )
    assert download_filename("Finals", SITTING_ID) == "finals-result.pdf"
