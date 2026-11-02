"""Copying what hangs off a consumer attempt: its debrief and its live coverage.

Neither Firestore collection names the attempt. A debrief names the user, mock and station; a
coverage document is keyed `<user>_<mock>_<station>`. Both are resolved through the transcripts
read in the same run, matched to whichever run was current AT THE TIME the debrief or coverage
was saved (`_run_at`), not always the newest: a candidate can retry a station after debriefing
the first attempt, and the retry must not steal the earlier debrief.

A legacy debrief becomes its own `kind="debrief"` attempt, exactly like a live one
(`service_debrief.start_debrief_attempt`), with `source_attempt_id` pointing at the consultation
it discusses. One station debriefed twice produces two debrief attempts, each with its own
summary - never one summary shared or overwritten. A summary written by an earlier, buggy run of
this importer directly onto the consultation attempt is moved onto its debrief attempt rather
than left in place or duplicated.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts.models import Attempt, AttemptLiveCoverage
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


def _runs_by_key(
    pairs: Sequence[tuple[MigratedAttempt, dict[str, Any]]],
) -> dict[tuple, list[tuple[datetime, str]]]:
    """Each `practice_key` mapped to every one of its attempts' `(created_at, legacy_ref)`, oldest first.

    A retried station has several; a debrief or coverage snapshot picks the one that was current
    when it was saved, via `_run_at`, rather than always the latest.
    """
    runs: dict[tuple, list[tuple[datetime, str]]] = {}
    for migrated, raw in pairs:
        runs.setdefault(practice_key(raw), []).append((migrated.created_at, legacy_ref_for(migrated)))
    for key_runs in runs.values():
        key_runs.sort(key=lambda run: run[0])
    return runs


def _run_at(runs: Sequence[tuple[datetime, str]], when: datetime | None) -> str | None:
    """The newest run at or before `when`; the newest run overall if `when` is unknown or earliest."""
    if not runs:
        return None
    if when is not None:
        at_or_before = [reference for run_at, reference in runs if run_at <= when]
        if at_or_before:
            return at_or_before[-1]
    return runs[-1][1]


async def _consultations_by_ref(session: AsyncSession, refs: Sequence[str]) -> dict[str, Attempt]:
    """Every already-loaded consultation attempt this run might debrief, keyed by its legacy reference."""
    found: dict[str, Attempt] = {}
    wanted = [ref for ref in set(refs) if ref]
    for start in range(0, len(wanted), 1000):
        chunk = wanted[start : start + 1000]
        rows = await session.scalars(select(Attempt).where(Attempt.legacy_ref.in_(chunk)))
        found.update({attempt.legacy_ref: attempt for attempt in rows if attempt.legacy_ref})
    return found


async def load_debriefs(
    session: AsyncSession,
    debriefs: Sequence[dict[str, Any]],
    pairs: Sequence[tuple[MigratedAttempt, dict]],
    lookups: Lookups,
) -> StepReport:
    """Load each legacy tutor debrief as its own debrief attempt, with the summary anchored to it."""
    report = StepReport()
    runs = _runs_by_key(pairs)
    all_refs = [reference for key_runs in runs.values() for _at, reference in key_runs]
    consultations = await _consultations_by_ref(session, all_refs)
    for debrief in debriefs:
        debrief_id = str(debrief.get("debrief_id") or debrief.get("id") or "")
        label = f"debrief {debrief_id}"
        try:
            exam_code = exam_for_product(debrief.get("app_type"))
        except UnknownLegacyProduct as exc:
            report.problem(f"{label}: {exc}")
            continue
        key_runs = runs.get(practice_key(debrief))
        when = parse_timestamp(debrief.get("created_at"))
        reference = _run_at(key_runs, when) if key_runs else None
        consultation = consultations.get(reference or "")
        if consultation is None:
            report.count("debriefs with no copied attempt (not copyable)")
            continue
        user_id = lookups.user(debrief.get("user_id"))
        if user_id is None:
            report.problem(f"{label}: no platform user for legacy user_id {debrief.get('user_id')!r}")
            continue
        attempt_id = legacy_row_id(f"{exam_code}:debrief-attempt:{debrief_id}")
        if await session.get(Attempt, attempt_id) is None:
            session.add(
                Attempt(
                    id=attempt_id,
                    kind="debrief",
                    user_id=user_id,
                    exam_id=consultation.exam_id,
                    org_id=consultation.org_id,
                    station_version_id=consultation.station_version_id,
                    source_attempt_id=consultation.id,
                    status="evaluated",
                    legacy_ref=f"{exam_code}:debrief-attempt:{debrief_id}",
                    definition=None,
                    **_when(debrief.get("created_at")),
                )
            )
            await session.flush()
            report.count("debrief attempts created")
        summary_id = legacy_row_id(f"{exam_code}:debrief:{debrief_id}")
        summary = await session.get(DebriefSummary, summary_id)
        if summary is None:
            session.add(
                DebriefSummary(
                    id=summary_id,
                    attempt_id=attempt_id,
                    user_id=user_id,
                    exam_id=lookups.exams.get(exam_code),
                    key_insights=list(debrief.get("key_insights") or []),
                    action_plan=list(debrief.get("action_plan") or []),
                    narrative=debrief.get("narrative_summary") or None,
                    model_used=LEGACY_MODEL,
                    **_when(debrief.get("created_at")),
                )
            )
            report.count("debriefs created")
        elif summary.attempt_id != attempt_id:
            summary.attempt_id = attempt_id
            report.count("debriefs re-anchored to their own debrief attempt")
        else:
            report.count("debriefs already there")
    await session.flush()
    return report


async def load_live_coverage(
    session: AsyncSession, documents: Sequence[dict[str, Any]], pairs: Sequence[tuple[MigratedAttempt, dict]]
) -> StepReport:
    """Load saved live-marking snapshots onto their attempts, matched by `<user>_<mock>_<station>`."""
    report = StepReport()
    runs = _runs_by_key(pairs)
    by_doc_id: dict[str, list[tuple[datetime, str]]] = {}
    for key, key_runs in runs.items():
        by_doc_id.setdefault("_".join(key[1:]), []).extend(key_runs)
    for key_runs in by_doc_id.values():
        key_runs.sort(key=lambda run: run[0])
    all_refs = [reference for key_runs in by_doc_id.values() for _at, reference in key_runs]
    ids = await attempt_ids_by_ref(session, all_refs)
    for coverage_document in documents:
        doc_runs = by_doc_id.get(str(coverage_document.get("id")))
        when = parse_timestamp(coverage_document.get("saved_at"))
        reference = _run_at(doc_runs, when) if doc_runs else None
        attempt_id = ids.get(reference or "")
        if attempt_id is None:
            report.count("coverage with no copied attempt (not copyable)")
            continue
        items = list(coverage_document.get("items") or [])
        snapshot = {
            "items": items,
            "last_seq": max(
                (int(item.get("seq") or 0) for item in items if isinstance(item, dict)), default=0
            ),
            "saved_at": coverage_document.get("saved_at"),
            "source": LEGACY_MODEL,
        }
        result = await session.execute(
            insert(AttemptLiveCoverage)
            .values(attempt_id=attempt_id, snapshot=snapshot)
            .on_conflict_do_nothing(index_elements=[AttemptLiveCoverage.attempt_id])
        )
        report.count("coverage created" if result.rowcount else "coverage already there")
    return report
