"""Copying consumer CVs, site messages and human (peer) practice sessions.

- **Site messages.** `messages` is the contact form and `features` is the
  feature-request box; they become the platform's `contact` and
  `product_feedback` kinds, which is the split `public_site` already draws.
- **Peer practice sessions** are historical, so every one lands `ended`, with
  the legacy status kept in `end_reason` (`legacy_completed`,
  `legacy_abandoned`). The recording key is kept, but the state stays `none`:
  the platform never scored these, and `stopped` would show the doctor
  "marking pending" for a mark that is never coming. Feedback comes from the
  doctor's own rating when there is one, else the patient's. Firestore's
  free-text `consultation_transcript` has no column and is not copied.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.cv.models import Cv
from app.features.peer_practice.models import PracticeSession
from app.features.public_site.models import SiteMessage
from app.migration.b2c_inventory import FEATURE_REQUEST_COLLECTIONS
from app.migration.b2c_lookups import Lookups, StepReport
from app.migration.legacy_ids import legacy_row_id
from app.migration.users import UnknownLegacyProduct, exam_for_product, parse_timestamp

_CV_STATUSES = {"processing", "completed", "failed"}
_FEATURE_COLLECTIONS = set(FEATURE_REQUEST_COLLECTIONS.values())


def _at(field: str, raw: object) -> dict[str, Any]:
    """A one-key kwargs dict for `field`, present only when `raw` parses to a timestamp.

    Lets a model constructor take `**_at("created_at", doc.get("created_at"))` and
    fall back to the column's own default when the legacy document has nothing.
    """
    at = parse_timestamp(raw)
    return {field: at} if at else {}


async def _add_once(session: AsyncSession, report: StepReport, row: Any, noun: str) -> None:
    """Add `row` unless a row with the same id is already there; either way, count it under `noun`."""
    if await session.get(type(row), row.id) is not None:
        report.count(f"{noun} already there")
        return
    session.add(row)
    report.count(f"{noun} created")


async def load_cvs(
    session: AsyncSession, documents: Sequence[dict[str, Any]], lookups: Lookups
) -> StepReport:
    """Load legacy CV uploads (`ortho_cvs` etc.) into `cvs`, skipping any whose owner is unresolved."""
    report = StepReport()
    for doc in documents:
        user_id = lookups.user(doc.get("user_id"))
        if user_id is None:
            report.problem(f"cv {doc.get('id')}: no platform user for legacy user_id {doc.get('user_id')!r}")
            continue
        status = str(doc.get("status") or "")
        cv = Cv(
            id=legacy_row_id(f"{doc.get('app_type') or 'ortho'}:cv:{doc.get('id')}"),
            user_id=user_id,
            status=status if status in _CV_STATUSES else "failed",
            original_filename=str(doc.get("original_filename") or doc.get("filename") or "")[:255],
            structured=doc.get("structured_cv") or None,
            error=None if status in _CV_STATUSES else f"legacy status {status!r}",
            completed_at=parse_timestamp(doc.get("completed_at")),
            **_at("created_at", doc.get("uploaded_at")),
        )
        await _add_once(session, report, cv, "cvs")
    await session.flush()
    return report


async def load_site_messages(
    session: AsyncSession, documents: Sequence[dict[str, Any]], lookups: Lookups
) -> StepReport:
    """Load legacy contact-form and feature-request documents into `site_messages`."""
    report = StepReport()
    for doc in documents:
        collection = str(doc.get("_collection") or "")
        feature = collection in _FEATURE_COLLECTIONS
        body = str(doc.get("feature" if feature else "message") or "").strip()
        if not body:
            report.count("site messages with no body (not copyable)")
            continue
        site_message = SiteMessage(
            id=legacy_row_id(f"site_message:{collection}:{doc.get('id')}"),
            kind="product_feedback" if feature else "contact",
            email=(str(doc.get("email") or "").strip() or None),
            subject=(str(doc.get("type" if feature else "subject") or "")[:200] or None),
            body=body,
            user_id=lookups.user(doc.get("created_by") or doc.get("user_id")),
            source=f"legacy-b2c:{collection}",
            **_at("created_at", doc.get("created_at")),
        )
        await _add_once(session, report, site_message, "site messages")
    await session.flush()
    return report


def _recording_key(doc: dict[str, Any]) -> str | None:
    """A peer-practice session's audio object key, stripped of its `s3://bucket/` prefix, or None."""
    path = str(doc.get("audio_s3_path") or "")
    if path.startswith("s3://"):
        return path.split("/", 3)[-1][:512] or None
    return None


def _feedback_for(session_doc: dict[str, Any], feedback: dict[str, list[dict]]) -> dict[str, Any]:
    """The doctor's own feedback for a peer-practice session if there is one, else the patient's, else {}."""
    feedback_rows = feedback.get(str(session_doc.get("session_id") or session_doc.get("id")), [])
    doctor = str(session_doc.get("doctor_user_id") or "")
    return next(
        (feedback_row for feedback_row in feedback_rows if str(feedback_row.get("user_id")) == doctor),
        feedback_rows[0] if feedback_rows else {},
    )


async def load_peer_practice(
    session: AsyncSession, sessions: Sequence[dict], feedbacks: Sequence[dict], lookups: Lookups
) -> StepReport:
    """Load legacy human peer-practice sessions into `practice_sessions`, all landing `ended`.

    The platform never scored these, so they get `recording_state="none"` rather
    than `stopped`, which would show a doctor "marking pending" for a mark that
    is never coming. Firestore's free-text `consultation_transcript` has no
    column on this model and is not copied.
    """
    report = StepReport()
    by_session: dict[str, list[dict]] = {}
    for feedback in feedbacks:
        by_session.setdefault(str(feedback.get("session_id") or ""), []).append(feedback)
    for doc in sessions:
        legacy_id = str(doc.get("session_id") or doc.get("id"))
        try:
            exam = exam_for_product(doc.get("app_type"))
        except UnknownLegacyProduct as exc:
            report.problem(f"practice session {legacy_id}: {exc}")
            continue
        doctor, patient = lookups.user(doc.get("doctor_user_id")), lookups.user(doc.get("patient_user_id"))
        if doctor is None or patient is None:
            report.problem(f"practice session {legacy_id}: doctor or patient is not a platform user")
            continue
        matched_feedback = _feedback_for(doc, by_session)
        rating = matched_feedback.get("experience_rating")
        practice_session = PracticeSession(
            id=legacy_row_id(f"{exam}:practice_session:{legacy_id}"),
            exam_id=lookups.exams[exam],
            doctor_user_id=doctor,
            patient_user_id=patient,
            station_version_id=lookups.station_version(exam, doc.get("station_id")),
            room_name=(str(doc.get("livekit_room_name") or "")[:200] or None),
            status="ended",
            end_reason=f"legacy_{doc.get('status') or 'unknown'}"[:32],
            doctor_joined_at=parse_timestamp(doc.get("doctor_joined_at")),
            patient_joined_at=parse_timestamp(doc.get("patient_joined_at")),
            preparation_started_at=parse_timestamp(doc.get("preparation_started_at")),
            ended_at=parse_timestamp(doc.get("ended_at")) or parse_timestamp(doc.get("created_at")),
            feedback_rating=int(rating) if isinstance(rating, int) else None,
            feedback_comment=(str(matched_feedback.get("feedback_text") or "")[:2000] or None),
            would_practice_again=matched_feedback.get("would_practice_again"),
            egress_id=(str(doc.get("audio_egress_id") or "")[:128] or None),
            recording_key=_recording_key(doc),
            recording_state="none",
            **_at("created_at", doc.get("created_at")),
        )
        await _add_once(session, report, practice_session, "practice sessions")
    await session.flush()
    return report
