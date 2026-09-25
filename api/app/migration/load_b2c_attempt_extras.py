"""Copying what hangs off a consumer attempt: its debrief and its live coverage.

Neither Firestore collection names the attempt. A debrief names the user, mock
and station; a coverage document is keyed `<user>_<mock>_<station>`. Both are
resolved through the transcripts read in the same run, newest attempt first,
because a retried station has several.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts.models import AttemptLiveCoverage
from app.features.tutor_memory.models import DebriefSummary
from app.migration.attempts import MigratedAttempt
from app.migration.b2c_lookups import Lookups, StepReport
from app.migration.legacy_ids import legacy_row_id
from app.migration.load_attempts import legacy_ref_for
from app.migration.load_b2c_attempts import attempt_ids_by_ref, practice_key
from app.migration.users import UnknownLegacyProduct, exam_for_product, parse_timestamp

LEGACY_MODEL = "legacy-b2c"


def _when(raw: object) -> dict[str, Any]:
    """`created_at` only when Firestore had one, so the column default applies otherwise."""
    at = parse_timestamp(raw)
    return {"created_at": at} if at else {}


def _refs_by_key(pairs: Sequence[tuple[MigratedAttempt, dict[str, Any]]]) -> dict[tuple, str]:
    newest = sorted(pairs, key=lambda p: p[0].created_at, reverse=True)
    out: dict[tuple, str] = {}
    for migrated, raw in newest:
        out.setdefault(practice_key(raw), legacy_ref_for(migrated))
    return out


async def load_debriefs(
    session: AsyncSession,
    debriefs: Sequence[dict[str, Any]],
    pairs: Sequence[tuple[MigratedAttempt, dict]],
    lookups: Lookups,
) -> StepReport:
    report = StepReport()
    refs = _refs_by_key(pairs)
    ids = await attempt_ids_by_ref(session, list(refs.values()))
    taken = set((await session.scalars(select(DebriefSummary.attempt_id))).all())
    for doc in sorted(debriefs, key=lambda d: str(d.get("created_at") or ""), reverse=True):
        label = f"debrief {doc.get('debrief_id') or doc.get('id')}"
        try:
            exam_code = exam_for_product(doc.get("app_type"))
        except UnknownLegacyProduct as exc:
            report.problem(f"{label}: {exc}")
            continue
        attempt_id = ids.get(refs.get(practice_key(doc), ""))
        if attempt_id is None:
            report.count("debriefs with no copied attempt (not copyable)")
            continue
        if attempt_id in taken:
            report.count("debriefs for an attempt that already has one")
            continue
        user_id = lookups.user(doc.get("user_id"))
        if user_id is None:
            report.problem(f"{label}: no platform user for legacy user_id {doc.get('user_id')!r}")
            continue
        session.add(
            DebriefSummary(
                id=legacy_row_id(f"{exam_code}:debrief:{doc.get('debrief_id') or doc.get('id')}"),
                attempt_id=attempt_id,
                user_id=user_id,
                exam_id=lookups.exams.get(exam_code),
                key_insights=list(doc.get("key_insights") or []),
                action_plan=list(doc.get("action_plan") or []),
                narrative=doc.get("narrative_summary") or None,
                model_used=LEGACY_MODEL,
                **_when(doc.get("created_at")),
            )
        )
        taken.add(attempt_id)
        report.count("debriefs created")
    await session.flush()
    return report


async def load_live_coverage(
    session: AsyncSession, documents: Sequence[dict[str, Any]], pairs: Sequence[tuple[MigratedAttempt, dict]]
) -> StepReport:
    report = StepReport()
    by_doc_id = {"_".join(key[1:]): ref for key, ref in _refs_by_key(pairs).items()}
    ids = await attempt_ids_by_ref(session, list(by_doc_id.values()))
    for doc in documents:
        attempt_id = ids.get(by_doc_id.get(str(doc.get("id")), ""))
        if attempt_id is None:
            report.count("coverage with no copied attempt (not copyable)")
            continue
        items = list(doc.get("items") or [])
        snapshot = {
            "items": items,
            "last_seq": max((int(i.get("seq") or 0) for i in items if isinstance(i, dict)), default=0),
            "saved_at": doc.get("saved_at"),
            "source": LEGACY_MODEL,
        }
        result = await session.execute(
            insert(AttemptLiveCoverage)
            .values(attempt_id=attempt_id, snapshot=snapshot)
            .on_conflict_do_nothing(index_elements=[AttemptLiveCoverage.attempt_id])
        )
        report.count("coverage created" if result.rowcount else "coverage already there")
    return report
