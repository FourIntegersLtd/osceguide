"""A released result as a PDF the candidate or their institution can keep.

One renderer, two callers. Both start from the candidate-facing projection,
so the file cannot contain moderation notes or the evidence snapshot, which
that projection does not carry. The face is a bundled Unicode font: names
outside Latin-1 have to render on a host that has no system fonts.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fpdf import FPDF
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.features.identity import service as identity
from app.features.results import errors, repository, service_candidate
from app.features.results.models import CandidateResultRevision
from app.features.results.schemas import TraineeResultRead
from app.features.roster import service as roster
from app.features.sittings import service_reads as sittings
from app.features.tenancy import service as tenancy
from app.features.tenancy import service_audit as audit

_FONT_FILE = Path(__file__).resolve().parent / "fonts" / "DejaVuSans.ttf"
# The assessment outcomes `SaveDecision` accepts, shown as words.
_OUTCOME_LABELS = {
    "pass": "Pass",
    "fail": "Fail",
    "inconclusive": "Inconclusive",
    "withheld": "Withheld",
}
_INK = (90, 90, 90)
_FOOTER_INK = (150, 150, 150)


class _ResultDocument(FPDF):
    """One released result. The footer is the only line that says when the file was made."""

    def __init__(self, generated: str) -> None:
        super().__init__(format="A4", unit="mm")
        self._generated = generated

    def footer(self) -> None:
        """The line at the foot of the page: when this file was generated."""
        self.set_y(-16)
        self.set_font("DejaVuSans", size=8)
        self.set_text_color(*_FOOTER_INK)
        self.cell(0, 5, self._generated)


def render_result_pdf(
    *,
    organisation_name: str,
    sitting_name: str,
    sitting_date: datetime | None,
    candidate_name: str,
    result: TraineeResultRead,
    generated_at: datetime,
) -> bytes:
    """The PDF bytes for one released result.

    The body is the candidate-facing fields plus the sitting they belong to.
    Nothing else from the decision record is accepted here, so it cannot leak.
    """
    document = _ResultDocument(_generated_line(generated_at))
    document.set_margins(18, 18, 18)
    document.set_auto_page_break(auto=True, margin=22)
    document.add_font("DejaVuSans", "", str(_FONT_FILE))
    document.add_page()
    _write_result(
        document,
        organisation_name=organisation_name,
        sitting_name=sitting_name,
        sitting_date=sitting_date,
        candidate_name=candidate_name,
        result=result,
    )
    # Subsetting the bundled face logs one line per table. A download is not
    # an operational event, so those lines stay off the request log.
    subset_log = logging.getLogger("fontTools")
    previous_level = subset_log.level
    subset_log.setLevel(logging.WARNING)
    try:
        produced = document.output()
    finally:
        subset_log.setLevel(previous_level)
    return bytes(produced)


async def render_my_result_pdf(
    session: AsyncSession,
    *,
    sitting_id: uuid.UUID,
    user_id: uuid.UUID,
    generated_at: datetime,
) -> tuple[bytes, str]:
    """The signed-in candidate's released result as a PDF.

    Goes through the same read as the result screen, so a result that has not
    been released is refused with `result_not_released` and nothing is written.
    """
    revision_row = await service_candidate.require_released_revision(session, sitting_id, user_id)
    result = await service_candidate.project_released_result(session, revision_row, user_id)
    return await _render_known_result(
        session, revision_row, result, generated_at, user_id=user_id, for_admin=False
    )


async def render_admin_result_pdf(
    session: AsyncSession,
    *,
    org_id: uuid.UUID,
    sitting_id: uuid.UUID,
    trainee_id: uuid.UUID,
    actor: Principal,
    generated_at: datetime,
) -> tuple[bytes, str]:
    """A released result as a PDF for an institution admin, with an audit row.

    A draft, or a sitting that is not this organisation's, is refused. The
    document is the same one the candidate downloads.
    """
    sitting = await sittings.sitting_ref(session, org_id, sitting_id)
    if sitting is None:
        raise errors.SittingNotFound()
    trainee = await roster.read_trainee(session, org_id, trainee_id)
    revision_row = await repository.released_revision(session, sitting_id, [trainee_id])
    if revision_row is None or revision_row.org_id != org_id:
        raise errors.NotReleased()
    result = await service_candidate.project_released_result(session, revision_row, trainee.user_id)
    payload, filename = await _render_known_result(
        session, revision_row, result, generated_at, user_id=trainee.user_id, for_admin=True
    )
    await audit.record_for_owner(
        session,
        org_id=org_id,
        actor=actor,
        action="results.exported",
        target_type="trainee",
        target_id=str(trainee_id),
        summary=f"Downloaded the released result for sitting {sitting_id} as a PDF",
        meta={"sitting_id": str(sitting_id), "format": "pdf"},
    )
    return payload, filename


async def _render_known_result(
    session: AsyncSession,
    revision_row: CandidateResultRevision,
    result: TraineeResultRead,
    generated_at: datetime,
    *,
    user_id: uuid.UUID | None,
    for_admin: bool,
) -> tuple[bytes, str]:
    """Look up the sitting the revision belongs to and render its PDF."""
    organisation = await tenancy.read_organization(session, revision_row.org_id)
    sitting = await sittings.sitting_ref(session, revision_row.org_id, revision_row.sitting_id)
    if sitting is None:
        raise errors.SittingNotFound()
    candidate_name = await _candidate_name(session, revision_row.org_id, revision_row.trainee_id, user_id)
    payload = render_result_pdf(
        organisation_name=organisation.name,
        sitting_name=sitting.name,
        sitting_date=sitting.scheduled_for,
        candidate_name=candidate_name,
        result=result,
        generated_at=generated_at,
    )
    filename = download_filename(
        sitting.name,
        sitting.id,
        candidate_name=candidate_name if for_admin else None,
        trainee_id=revision_row.trainee_id if for_admin else None,
    )
    return payload, filename


async def _candidate_name(
    session: AsyncSession,
    org_id: uuid.UUID,
    trainee_id: uuid.UUID,
    user_id: uuid.UUID | None,
) -> str:
    """The person's account name, or the roster name when they have not signed in. An
    anonymised entry is named by the roster alone (S-21)."""
    trainee = await roster.read_trainee(session, org_id, trainee_id)
    person = None
    if user_id is not None:
        person = (await identity.user_refs_by_ids(session, [user_id])).get(user_id)
    name, _ = roster.shown_identity(trainee, person)
    if name and name.strip():
        return name
    given = " ".join(part for part in (trainee.first_name, trainee.last_name) if part)
    return given or trainee.email


def _write_result(
    document: _ResultDocument,
    *,
    organisation_name: str,
    sitting_name: str,
    sitting_date: datetime | None,
    candidate_name: str,
    result: TraineeResultRead,
) -> None:
    """Title, the sitting it belongs to, then the candidate-facing fields."""
    document.set_text_color(*_INK)
    document.set_font("DejaVuSans", size=18)
    document.cell(0, 10, "Assessment result", new_x="LMARGIN", new_y="NEXT")
    document.set_font("DejaVuSans", size=12)
    document.cell(0, 7, organisation_name, new_x="LMARGIN", new_y="NEXT")
    document.cell(0, 7, sitting_name, new_x="LMARGIN", new_y="NEXT")
    document.ln(6)
    rows = [
        ("Candidate", candidate_name),
        ("Date of sitting", _human_date(sitting_date) if sitting_date else "Not scheduled"),
        ("Outcome", _outcome_label(result.assessment_outcome)),
        ("Score", _score(result.assessment_score)),
        ("Released", _human_datetime(result.released_at) if result.released_at else ""),
    ]
    if result.acknowledged_at is not None:
        rows.append(("Acknowledged", _human_datetime(result.acknowledged_at)))
    document.set_font("DejaVuSans", size=11)
    for label, value in rows:
        document.cell(46, 8, label)
        document.cell(0, 8, value, new_x="LMARGIN", new_y="NEXT")
    document.ln(6)
    document.cell(0, 8, "Rationale", new_x="LMARGIN", new_y="NEXT")
    document.multi_cell(0, 6, result.rationale or "")


def _score(value: float | None) -> str:
    """The candidate's score, or the words used when none was recorded."""
    if value is None:
        return "Not recorded"
    return f"{value:.1f}"


def _outcome_label(outcome: str | None) -> str:
    """The outcome in words. An unknown value is shown capitalised rather than dropped."""
    if not outcome:
        return ""
    known = _OUTCOME_LABELS.get(outcome)
    if known is not None:
        return known
    return outcome.replace("_", " ").capitalize()


def _human_date(moment: datetime) -> str:
    """A calendar day in UTC, with no leading zero: `20 September 2026`."""
    utc = moment.astimezone(UTC)
    return f"{utc.day} {utc.strftime('%B')} {utc.year}"


def _human_datetime(moment: datetime) -> str:
    """An instant in UTC: `20 September 2026, 12:04 UTC`."""
    utc = moment.astimezone(UTC)
    return f"{_human_date(moment)}, {utc.strftime('%H:%M')} UTC"


def _generated_line(generated_at: datetime) -> str:
    return f"Generated {_human_datetime(generated_at)}"


def download_filename(
    sitting_name: str,
    sitting_id: uuid.UUID,
    *,
    candidate_name: str | None = None,
    trainee_id: uuid.UUID | None = None,
) -> str:
    """The download name. An admin's file names the candidate; the candidate's own does not."""
    sitting = _filename_stem(sitting_name, sitting_id)
    if candidate_name is None:
        return f"{sitting}-result.pdf"
    candidate = re.sub(r"[^a-z0-9]+", "-", candidate_name.casefold()).strip("-")
    if not candidate:
        candidate = str(trainee_id if trainee_id is not None else sitting_id)
    return f"{sitting}-{candidate}-result.pdf"


def _filename_stem(sitting_name: str, sitting_id: uuid.UUID) -> str:
    """A file-name stem: the sitting's name as a slug, or its id."""
    slug = re.sub(r"[^a-z0-9]+", "-", sitting_name.casefold()).strip("-")
    return slug or str(sitting_id)
