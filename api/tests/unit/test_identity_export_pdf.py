"""A-31: the export PDF is a readable document: tables, a score line, no raw JSON."""

from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime

from pypdf import PdfReader

from app.core.schemas import DomainTotalRead, RatingRead, ResultTotalsRead
from app.features.attempts.schemas import AttemptFeedbackRead, MarkedResultRead, MarkingRubricRead
from app.features.identity.schemas import (
    ExportedAttempt,
    ExportedPayment,
    ExportedProfile,
    ExportedResult,
    ExportedTranscript,
    ExportedTranscriptMessage,
    MyDataExport,
)
from app.features.identity.service_export import ExportBundle, render_export_pdf
from tests.support.rubrics import MINIMAL_RUBRIC

AT = datetime(2026, 9, 20, 14, 5, tzinfo=UTC)
PAYLOAD = {"consulting": {"opens_well": {"score": "G"}}, "gathered_by": {"history_taken": True}}
ATTEMPT_ID = uuid.uuid4()


def _export(payload: dict[str, object], message: str = "What brought you in today?") -> MyDataExport:
    return MyDataExport(
        profile=ExportedProfile(
            id=uuid.uuid4(), email="anna@example.com", name="Анна Петрова", created_at=AT
        ),
        attempts=[
            ExportedAttempt(
                id=ATTEMPT_ID,
                kind="consultation",
                status="completed",
                started_at=AT,
                completed_at=AT,
                transcript=ExportedTranscript(
                    complete=True,
                    messages=[ExportedTranscriptMessage(role="patient", message=message, spoken_at=AT)],
                ),
                results=[
                    ExportedResult(framework_id="sca", policy_version="v1", payload=payload, scored_at=AT)
                ],
            )
        ],
        payments=[
            ExportedPayment(
                receipt_id="R-1", amount_total_pence=4999, amount_tax_pence=833, currency="gbp", paid_at=AT
            )
        ],
    )


def _rubric_structure() -> dict[str, object]:
    from app.features.rubrics import domain

    return domain.upgrade_structure(MINIMAL_RUBRIC)


def _feedback() -> AttemptFeedbackRead:
    structure = _rubric_structure()
    return AttemptFeedbackRead(
        attempt_id=ATTEMPT_ID,
        rubric=MarkingRubricRead(
            version_id=None,
            structure=structure,
            display={},
            rating=RatingRead(kind="enum", field="score", scale=["R", "A", "G"]),
        ),
        results=[
            MarkedResultRead(
                framework_id="sca",
                policy_version="v1",
                model_used=None,
                payload=PAYLOAD,
                scored_at=AT,
                totals=ResultTotalsRead(
                    total=2,
                    max=3,
                    fraction=0.67,
                    passed=True,
                    critical_count=0,
                    domains=[DomainTotalRead(id="consulting", label="Consulting", value=2, passed=True)],
                ),
            )
        ],
    )


def _text(bundle: ExportBundle) -> str:
    return "".join(page.extract_text() for page in PdfReader(io.BytesIO(render_export_pdf(bundle))).pages)


def test_a_marked_attempt_reads_as_a_score_line_and_a_domain_table() -> None:
    text = _text(ExportBundle(_export(PAYLOAD), {ATTEMPT_ID: _feedback()}))

    assert "Анна Петрова" in text
    assert "Consulting" in text
    assert "2 of 3 · Passed · 0 critical concerns" in text
    assert "£49.99" in text
    assert "R-1" in text
    assert "Page 1 of" in text
    assert "20 September 2026, 14:05 UTC" in text
    assert "{" not in text


def test_a_long_unbroken_turn_reaches_the_file() -> None:
    text = _text(ExportBundle(_export(PAYLOAD, message="x" * 2_000), {ATTEMPT_ID: _feedback()}))

    assert text.replace("\n", "").count("x") >= 2_000


def test_a_mark_no_rubric_can_read_falls_back_to_humanised_labels() -> None:
    text = _text(ExportBundle(_export(PAYLOAD), {}))

    assert "Gathered by" in text
    assert "History taken" in text
    assert "{" not in text
