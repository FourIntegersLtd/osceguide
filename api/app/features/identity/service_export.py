"""A person's own data, as one JSON download (E-5), or the same data as a PDF (A-31).

UK GDPR gives a month to answer a subject access request; this route answers
it immediately, self-serve, by reusing the services the rest of the app
already reads through — no new read model, no new layer. It intentionally
does not aggregate an institution's decision about the person (that is the
organisation's record, not something this route can hand over on the
person's say-so alone); it is everything this account owns: its own profile,
its own attempts with their transcripts and marks, and its own payments.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, date, datetime

from fpdf import FPDF
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import pdf
from app.features.attempts import service_privacy as attempts_privacy
from app.features.billing import service_receipts as billing_receipts
from app.features.identity import repository
from app.features.identity.errors import AccountNotFound
from app.features.identity.schemas import (
    ExportedAttempt,
    ExportedPayment,
    ExportedProfile,
    ExportedResult,
    ExportedTranscript,
    ExportedTranscriptMessage,
    MyDataExport,
)


async def export_my_data(session: AsyncSession, *, user_id: uuid.UUID) -> MyDataExport:
    """Everything `user_id` owns, ready to serialise as the export download.

    Raises `AccountNotFound` if the account is gone — a closed account can still
    sign in during the 30-day window before erasure, so this stays reachable
    right up until the erasure job runs.
    """
    user = await repository.user_by_id(session, user_id)
    if user is None:
        raise AccountNotFound()

    attempts = await attempts_privacy.export_for_user(session, user_id)
    payments = await billing_receipts.export_payments_for_user(session, user_id)

    return MyDataExport(
        profile=ExportedProfile(
            id=user.id,
            email=user.email,
            name=user.name,
            exam_code=user.exam_code,
            exam_date=user.exam_date,
            created_at=user.created_at,
        ),
        attempts=[
            ExportedAttempt(
                id=attempt["id"],
                kind=attempt["kind"],
                status=attempt["status"],
                started_at=attempt["started_at"],
                completed_at=attempt["completed_at"],
                transcript=ExportedTranscript(
                    complete=attempt["transcript"]["complete"],
                    messages=[
                        ExportedTranscriptMessage(**message) for message in attempt["transcript"]["messages"]
                    ],
                ),
                results=[ExportedResult(**result) for result in attempt["results"]],
            )
            for attempt in attempts
        ],
        payments=[ExportedPayment(**payment) for payment in payments],
    )


async def export_my_data_pdf(session: AsyncSession, *, user_id: uuid.UUID) -> bytes:
    """The same export as `export_my_data`, as a PDF a person can read and print.

    Built from the `MyDataExport` itself, so the file holds exactly what the JSON
    download holds and nothing a later read model adds.
    """
    export = await export_my_data(session, user_id=user_id)
    # Rendering is CPU-bound and a long history takes seconds; off the event loop it blocks no one.
    return await asyncio.to_thread(render_export_pdf, export)


def render_export_pdf(export: MyDataExport) -> bytes:
    """Profile, then every attempt with its marks and transcript, then payments."""
    document = FPDF(format="A4", unit="mm")
    document.set_margins(18, 18, 18)
    document.set_auto_page_break(auto=True, margin=18)
    pdf.add_face(document)
    document.add_page()

    _heading(document, "Your OSCE Guide data", size=18)
    profile = export.profile
    _rows(
        document,
        [
            ("Name", profile.name),
            ("Email", profile.email),
            ("Exam", profile.exam_code or "Not chosen"),
            ("Exam date", _day(profile.exam_date) if profile.exam_date else "Not set"),
            ("Account created", _moment(profile.created_at)),
        ],
    )

    _heading(document, f"Attempts ({len(export.attempts)})")
    if not export.attempts:
        _line(document, "No attempts.")
    for attempt in export.attempts:
        _heading(document, f"{attempt.kind.replace('_', ' ').capitalize()} · {attempt.status}", size=12)
        _rows(
            document,
            [
                ("Attempt", str(attempt.id)),
                ("Started", _moment(attempt.started_at) if attempt.started_at else "Not started"),
                ("Completed", _moment(attempt.completed_at) if attempt.completed_at else "Not completed"),
            ],
        )
        for result in attempt.results:
            scored = _moment(result.scored_at)
            _line(document, f"Mark: {result.framework_id} ({result.policy_version}), {scored}")
            _line(document, json.dumps(result.payload, indent=2, default=str, ensure_ascii=False), size=8)
        transcript_state = "complete" if attempt.transcript.complete else "incomplete"
        _line(document, f"Transcript ({transcript_state})")
        for message in attempt.transcript.messages:
            _line(document, f"{_moment(message.spoken_at)}  {message.role}: {message.message}")

    _heading(document, f"Payments ({len(export.payments)})")
    if not export.payments:
        _line(document, "No payments.")
    for payment in export.payments:
        amount = f"{payment.amount_total_pence / 100:.2f} {payment.currency.upper()}"
        receipt = f", receipt {payment.receipt_id}" if payment.receipt_id else ""
        _line(document, f"{_moment(payment.paid_at)}  {amount}{receipt}")
    return pdf.output_bytes(document)


def _heading(document: FPDF, text: str, *, size: int = 14) -> None:
    """A section title with a little space above it."""
    document.ln(4)
    document.set_font(pdf.FACE, size=size)
    document.multi_cell(0, size * 0.5, text, new_x="LMARGIN", new_y="NEXT")


def _rows(document: FPDF, rows: list[tuple[str, str]]) -> None:
    """Label and value pairs, one per line."""
    document.set_font(pdf.FACE, size=10)
    for label, value in rows:
        document.cell(40, 6, label)
        document.multi_cell(0, 6, value, new_x="LMARGIN", new_y="NEXT")


def _line(document: FPDF, text: str, *, size: int = 10) -> None:
    """One wrapped paragraph."""
    document.set_font(pdf.FACE, size=size)
    document.multi_cell(0, size * 0.5, text, new_x="LMARGIN", new_y="NEXT")


def _moment(moment: datetime) -> str:
    """A UTC timestamp to the minute: `20 September 2026, 14:05 UTC`."""
    utc = moment.astimezone(UTC)
    return f"{_day(utc.date())}, {utc.strftime('%H:%M')} UTC"


def _day(day: date) -> str:
    """A calendar day with no leading zero: `20 September 2026`."""
    return f"{day.day} {day.strftime('%B')} {day.year}"
