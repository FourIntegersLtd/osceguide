"""A-31: the export PDF renders text the JSON carries, Latin or not, however long."""

from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime

from pypdf import PdfReader

from app.features.identity.schemas import (
    ExportedAttempt,
    ExportedPayment,
    ExportedProfile,
    ExportedTranscript,
    ExportedTranscriptMessage,
    MyDataExport,
)
from app.features.identity.service_export import render_export_pdf

AT = datetime(2026, 9, 20, 14, 5, tzinfo=UTC)


def test_a_cyrillic_name_a_long_unbroken_turn_and_a_payment_all_reach_the_file() -> None:
    unbroken = "x" * 2_000
    export = MyDataExport(
        profile=ExportedProfile(
            id=uuid.uuid4(), email="anna@example.com", name="Анна Петрова", created_at=AT
        ),
        attempts=[
            ExportedAttempt(
                id=uuid.uuid4(),
                kind="consultation",
                status="completed",
                started_at=AT,
                completed_at=AT,
                transcript=ExportedTranscript(
                    complete=True,
                    messages=[ExportedTranscriptMessage(role="patient", message=unbroken, spoken_at=AT)],
                ),
            )
        ],
        payments=[
            ExportedPayment(
                receipt_id="R-1", amount_total_pence=4999, amount_tax_pence=833, currency="gbp", paid_at=AT
            )
        ],
    )

    text = "".join(page.extract_text() for page in PdfReader(io.BytesIO(render_export_pdf(export))).pages)

    assert "Анна Петрова" in text
    assert "anna@example.com" in text
    assert text.replace("\n", "").count("x") >= 2_000
    assert "49.99 GBP, receipt R-1" in text
    assert "20 September 2026, 14:05 UTC" in text
