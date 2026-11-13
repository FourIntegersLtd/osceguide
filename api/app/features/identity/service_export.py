"""A person's own data, as a PDF a lay reader can print (E-5, A-31).

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
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from fpdf import FPDF
from fpdf.fonts import FontFace
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import pdf
from app.features.attempts import service_feedback as attempts_feedback
from app.features.attempts import service_privacy as attempts_privacy
from app.features.attempts.schemas import AttemptFeedbackRead, MarkedResultRead
from app.features.billing import service_receipts as billing_receipts
from app.features.identity import repository
from app.features.identity.errors import AccountNotFound
from app.features.identity.schemas import (
    ExportedAttempt,
    ExportedNonverbalConsent,
    ExportedPayment,
    ExportedProfile,
    ExportedResult,
    ExportedTranscript,
    ExportedTranscriptMessage,
    MyDataExport,
)
from app.features.rubrics import service_marking as rubrics_marking
from app.features.rubrics import service_scoring as rubrics_scoring


async def export_my_data(session: AsyncSession, *, user_id: uuid.UUID) -> MyDataExport:
    """Everything `user_id` owns, the export the PDF is built from.

    Raises `AccountNotFound` if the account is gone — a closed account can still
    sign in during the 30-day window before erasure, so this stays reachable
    right up until the erasure job runs.
    """
    user = await repository.user_by_id(session, user_id)
    if user is None:
        raise AccountNotFound()

    attempts = await attempts_privacy.export_for_user(session, user_id)
    consent = await attempts_privacy.export_nonverbal_consent_for_user(session, user_id)
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
                nonverbal=attempt["nonverbal"],
                results=[ExportedResult(**result) for result in attempt["results"]],
            )
            for attempt in attempts
        ],
        nonverbal_consent=ExportedNonverbalConsent(**consent) if consent else None,
        payments=[ExportedPayment(**payment) for payment in payments],
    )


@dataclass(frozen=True)
class ExportBundle:
    """The export plus, per attempt, the rubric and totals that read its marks.

    Kept beside `MyDataExport` rather than in it: identity's schemas may not
    import attempts' schemas.
    """

    export: MyDataExport
    feedback: dict[uuid.UUID, AttemptFeedbackRead]


async def export_my_data_pdf(session: AsyncSession, *, user_id: uuid.UUID) -> bytes:
    """The export as a PDF a person can read and print."""
    export = await export_my_data(session, user_id=user_id)
    # One read per attempt: reuses the feedback service's access check and frozen rubric.
    feedback = {
        attempt.id: await attempts_feedback.read_feedback(
            session, attempt.id, requester_id=user_id, is_admin=False
        )
        for attempt in export.attempts
    }
    # Rendering is CPU-bound and a long history takes seconds; off the event loop it blocks no one.
    return await asyncio.to_thread(render_export_pdf, ExportBundle(export, feedback))


_INK = (90, 90, 90)
_FOOTER_INK = (150, 150, 150)
_HEADER = FontFace(color=(255, 255, 255), fill_color=(70, 90, 120))
_CURRENCY_SYMBOLS = {"gbp": "£", "usd": "$", "eur": "€"}
_ROLE_LABELS = {"doctor": "Candidate", "candidate": "Candidate", "patient": "Patient", "examiner": "Examiner"}
_FEEDBACK_ROLES = (("summary", "Summary"), ("explanation", "Explanation"), ("evidence", "Evidence"))
_LABEL_WIDTH = 50
_CONTENT_WIDTH = 174  # A4 less the 18 mm margins


class _ExportDocument(FPDF):
    """The export. The footer says when it was made and which page this is."""

    def __init__(self, generated: str) -> None:
        super().__init__(format="A4", unit="mm")
        self._generated = generated

    def footer(self) -> None:
        """The line at the foot of each page: when this file was made and the page number."""
        self.set_y(-14)
        self.set_font(pdf.FACE, size=8)
        self.set_text_color(*_FOOTER_INK)
        self.cell(0, 5, f"Generated {self._generated} · Page {self.page_no()} of {{nb}}")


def render_export_pdf(bundle: ExportBundle, *, generated_at: datetime | None = None) -> bytes:
    """Title, profile, every attempt with its marks and transcript, then payments."""
    export = bundle.export
    document = _ExportDocument(_moment(generated_at or datetime.now(UTC)))
    document.alias_nb_pages()
    document.set_margins(18, 18, 18)
    document.set_auto_page_break(auto=True, margin=20)
    pdf.add_face(document)
    document.add_page()
    _title(document, "Your OSCE Guide data", size=20)
    _paragraph(document, f"Everything the account {export.profile.email} holds, as of {document._generated}.")
    _paragraph(
        document,
        f"Contents: Your profile · Your attempts ({len(export.attempts)})"
        f" · Your payments ({len(export.payments)})",
    )
    _write_profile(document, export.profile)
    _write_attempts(document, bundle)
    _write_payments(document, export.payments)
    return pdf.output_bytes(document)


def _write_profile(document: FPDF, profile: ExportedProfile) -> None:
    """The account's own fields."""
    _title(document, "Your profile")
    _facts(
        document,
        [
            ("Name", profile.name),
            ("Email", profile.email),
            ("Exam", profile.exam_code or "Not chosen"),
            ("Exam date", _day(profile.exam_date) if profile.exam_date else "Not set"),
            ("Account created", _moment(profile.created_at)),
            ("Account id", str(profile.id)),
        ],
    )


def _write_attempts(document: FPDF, bundle: ExportBundle) -> None:
    """An overview table, then each attempt in full, or a line saying there are none."""
    attempts = bundle.export.attempts
    _title(document, f"Your attempts ({len(attempts)})")
    if not attempts:
        _paragraph(document, "No attempts.")
        return
    _table(
        document,
        ["#", "Kind", "Status", "Started", "Completed", "Marks"],
        [
            [
                str(number),
                _words(attempt.kind),
                _words(attempt.status),
                _when(attempt.started_at, "Not started"),
                _when(attempt.completed_at, "Not completed"),
                str(len(attempt.results)),
            ]
            for number, attempt in enumerate(attempts, start=1)
        ],
        widths=(8, 26, 30, 44, 44, 22),
    )
    for number, attempt in enumerate(attempts, start=1):
        _title(document, f"Attempt {number} · {_words(attempt.kind)} · {_words(attempt.status)}", size=13)
        _facts(
            document,
            [
                ("Attempt id", str(attempt.id)),
                ("Started", _when(attempt.started_at, "Not started")),
                ("Completed", _when(attempt.completed_at, "Not completed")),
                ("Transcript complete", "Yes" if attempt.transcript.complete else "No"),
            ],
        )
        _write_marks(document, attempt, bundle.feedback.get(attempt.id))
        _write_transcript(document, attempt)


def _write_marks(document: FPDF, attempt: ExportedAttempt, feedback: AttemptFeedbackRead | None) -> None:
    """Each stored mark: a score line and domain table when a rubric reads it, else plain label/value rows."""
    if not attempt.results:
        _paragraph(document, "No marks yet.")
        return
    rubric = (
        rubrics_marking.frozen_scoring_rubric(
            {"structure": feedback.rubric.structure, "display": feedback.rubric.display}
        )
        if feedback and feedback.rubric
        else None
    )
    marked = feedback.results if feedback else []
    for index, result in enumerate(attempt.results):
        _title(
            document,
            f"Mark {index + 1} of {len(attempt.results)}, scored {_moment(result.scored_at)}",
            size=11,
        )
        if rubric is None:
            _write_generic(document, result.payload)
        else:
            _write_rubric_mark(
                document, rubric, result.payload, marked[index] if index < len(marked) else None
            )


def _write_rubric_mark(
    document: FPDF,
    rubric: rubrics_marking.ScoringRubric,
    payload: Mapping[str, Any],
    marked: MarkedResultRead | None,
) -> None:
    """Score line, the domain table and the written feedback of one mark."""
    structure = rubric.structure
    totals = marked.totals if marked else None
    if totals is not None and totals.total is not None and totals.max is not None:
        verdict = "" if totals.passed is None else (" · Passed" if totals.passed else " · Not passed")
        concerns = totals.critical_count
        _paragraph(
            document,
            f"{totals.total:g} of {totals.max:g}{verdict} · {concerns} critical "
            f"concern{'' if concerns == 1 else 's'}",
            size=12,
        )
    ratings = rubrics_scoring.ratings_in(structure, payload)
    results = {domain_total.id: domain_total for domain_total in totals.domains} if totals else {}
    rows = []
    for domain in structure.domains:
        if domain.id not in ratings:
            continue
        domain_total = results.get(domain.id)
        result = ""
        if domain_total and domain_total.value is not None:
            result = f"{domain_total.value:g}"
            if domain_total.passed is not None:
                result += " · Passed" if domain_total.passed else " · Not passed"
        rows.append(
            [
                domain.title,
                ", ".join(str(rating) for rating in ratings[domain.id]) or "Not rated",
                result or "-",
            ]
        )
    if rows:
        _table(document, ["Domain", "Ratings", "Result"], rows, widths=(70, 64, 40))
    written = rubrics_scoring.texts_by_role(structure, payload, roles=[role for role, _ in _FEEDBACK_ROLES])
    for role, title in _FEEDBACK_ROLES:
        if written[role]:
            _title(document, title, size=10)
            for text in written[role]:
                _paragraph(document, text)


def _write_generic(document: FPDF, payload: Mapping[str, Any], depth: int = 0) -> None:
    """A mark no rubric can read: humanised labels, nested groups as headings, lists as bullets."""
    plain = [
        (_words(str(key)), _plain(value))
        for key, value in payload.items()
        if not isinstance(value, (Mapping, list))
    ]
    if plain:
        _facts(document, plain)
    for key, value in payload.items():
        if isinstance(value, Mapping):
            _title(document, _words(str(key)), size=max(9, 10 - depth))
            _write_generic(document, value, depth + 1)
        elif isinstance(value, list):
            _title(document, _words(str(key)), size=max(9, 10 - depth))
            for entry in value:
                _paragraph(document, f"• {_plain(entry)}")


def _plain(value: object) -> str:
    """A leaf value as a person writes it."""
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return str(value)


def _write_transcript(document: FPDF, attempt: ExportedAttempt) -> None:
    """Who said what, when."""
    _title(document, "Transcript", size=11)
    if not attempt.transcript.messages:
        _paragraph(document, "No transcript was recorded.")
        return
    _table(
        document,
        ["Time", "Who", "Said"],
        [
            [
                _moment(message.spoken_at),
                _ROLE_LABELS.get(message.role, _words(message.role)),
                message.message,
            ]
            for message in attempt.transcript.messages
        ],
        widths=(48, 24, 102),
    )


def _write_payments(document: FPDF, payments: list[ExportedPayment]) -> None:
    """Every payment, or a line saying there are none."""
    _title(document, f"Your payments ({len(payments)})")
    if not payments:
        _paragraph(document, "No payments.")
        return
    _table(
        document,
        ["Date", "Amount", "Tax", "Receipt"],
        [
            [
                _moment(payment.paid_at),
                _money(payment.amount_total_pence, payment.currency),
                _money(payment.amount_tax_pence, payment.currency),
                payment.receipt_id or "-",
            ]
            for payment in payments
        ],
        widths=(56, 30, 30, 58),
    )
    for payment in payments:
        if payment.receipt_url:
            _paragraph(
                document,
                f"Receipt {payment.receipt_id}: {payment.receipt_url}"
                if payment.receipt_id
                else f"Receipt: {payment.receipt_url}",
                size=8,
            )


def _title(document: FPDF, text: str, *, size: int = 15) -> None:
    """A heading with space above it, kept with the line that follows."""
    document.ln(4)
    document.set_font(pdf.FACE, size=size)
    document.set_text_color(30, 30, 30)
    document.multi_cell(0, size * 0.55, text, new_x="LMARGIN", new_y="NEXT")
    document.ln(1)


def _paragraph(document: FPDF, text: str, *, size: int = 10) -> None:
    """One wrapped paragraph in body ink."""
    document.set_font(pdf.FACE, size=size)
    document.set_text_color(*_INK)
    document.multi_cell(0, size * 0.5, text, new_x="LMARGIN", new_y="NEXT")


def _facts(document: FPDF, rows: list[tuple[str, str]]) -> None:
    """Label and value pairs as a two-column table with no header row."""
    document.set_font(pdf.FACE, size=10)
    document.set_text_color(*_INK)
    with document.table(
        col_widths=(_LABEL_WIDTH, _CONTENT_WIDTH - _LABEL_WIDTH),
        first_row_as_headings=False,
        line_height=6,
        text_align="LEFT",
    ) as table:
        for label, value in rows:
            row = table.row()
            row.cell(label)
            row.cell(value)


def _table(document: FPDF, header: list[str], rows: list[list[str]], *, widths: tuple[float, ...]) -> None:
    """A table with a header row that repeats on each page."""
    document.set_font(pdf.FACE, size=9)
    document.set_text_color(*_INK)
    with document.table(
        col_widths=widths, headings_style=_HEADER, line_height=5.5, text_align="LEFT"
    ) as table:
        head = table.row()
        for name in header:
            head.cell(name)
        for values in rows:
            row = table.row()
            for value in values:
                row.cell(value)


def _money(pence: int, currency: str) -> str:
    """`£49.99` for a currency with a symbol, else `49.99 CHF`."""
    symbol = _CURRENCY_SYMBOLS.get(currency.lower())
    amount = f"{pence / 100:.2f}"
    return f"{symbol}{amount}" if symbol else f"{amount} {currency.upper()}"


def _words(key: str) -> str:
    """`interaction_complete` to `Interaction complete`."""
    return key.replace("_", " ").capitalize()


def _when(moment: datetime | None, missing: str) -> str:
    """A timestamp, or the words for it being absent."""
    return _moment(moment) if moment else missing


def _moment(moment: datetime) -> str:
    """A UTC timestamp to the minute: `20 September 2026, 14:05 UTC`."""
    utc = moment.astimezone(UTC)
    return f"{_day(utc.date())}, {utc.strftime('%H:%M')} UTC"


def _day(day: date) -> str:
    """A calendar day with no leading zero: `20 September 2026`."""
    return f"{day.day} {day.strftime('%B')} {day.year}"
