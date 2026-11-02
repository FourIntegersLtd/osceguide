"""Does the platform database hold everything the legacy Firestore holds?

Read-only. Each `reconcile_*` function takes the legacy documents (already streamed, seed rows
dropped) and returns one `Finding` per document that did NOT arrive correctly, with a reason code.
A document that was left out on purpose (deleted account, no email) is still listed but marked
`expected`, so the defects are only the rows nobody meant to drop.

Nothing here writes. The command line wrapper is `scripts/reconcile_legacy.py`.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts.models import AssessmentResult, Attempt, Transcript, TranscriptMessage
from app.features.billing.models import Payment
from app.features.entitlements.models import Entitlement
from app.features.identity.models import User
from app.migration import b2c_lookups
from app.migration.attempts import attempt_from_transcript
from app.migration.b2c_lookups import StepReport
from app.migration.load_attempts import legacy_ref_for
from app.migration.load_b2c_attempts import migrate_transcripts
from app.migration.users import normalize_email, parse_timestamp


@dataclass(frozen=True)
class Finding:
    """One legacy document that is missing or wrong in the platform database."""

    entity: str
    legacy_id: str
    collection: str
    reason: str
    # True when the row was left out on purpose (deleted account, no email): listed, not a defect.
    expected: bool = False
    detail: str = ""


def _text(value: object) -> str:
    """A document field as a stripped string; empty when absent."""
    return str(value or "").strip()


async def reconcile_users(
    session: AsyncSession, documents: Iterable[dict[str, Any]], deleted_ids: set[str]
) -> list[Finding]:
    """Users whose legacy document id is not linked to a platform user."""
    lookups = await b2c_lookups.build(session)
    findings: list[Finding] = []
    for document in documents:
        legacy_id = _text(document.get("id"))
        collection = _text(document.get("_collection"))
        if lookups.user(legacy_id) is not None:
            if legacy_id in deleted_ids or document.get("is_deleted") is True:
                # Asked to be forgotten in the old app but present here: a defect to repair.
                findings.append(Finding("users", legacy_id, collection, "imported_but_deleted"))
            continue
        if legacy_id in deleted_ids or document.get("is_deleted") is True:
            findings.append(Finding("users", legacy_id, collection, "deleted", expected=True))
        elif not normalize_email(document.get("email")):
            findings.append(Finding("users", legacy_id, collection, "no_email", expected=True))
        elif (merged_into := lookups.user_by_email(document.get("email"))) is not None:
            # Another product's account with the same email carries this person.
            findings.append(
                Finding("users", legacy_id, collection, "merged_into", expected=True, detail=str(merged_into))
            )
        else:
            findings.append(Finding("users", legacy_id, collection, "missing"))
    return findings


async def reconcile_stations(session: AsyncSession, documents: Iterable[dict[str, Any]]) -> list[Finding]:
    """Stations with no imported version under their exam."""
    lookups = await b2c_lookups.build(session)
    findings: list[Finding] = []
    for document in documents:
        legacy_id = _text(document.get("station_id")) or _text(document.get("id"))
        exam = _text(document.get("app_type")).lower()
        collection = _text(document.get("_collection"))
        if exam not in lookups.exams:
            findings.append(Finding("stations", legacy_id, collection, "unknown_exam", detail=exam))
        elif lookups.station_version(exam, legacy_id) is None:
            findings.append(Finding("stations", legacy_id, collection, "missing"))
    return findings


async def reconcile_attempts(
    session: AsyncSession,
    transcripts: Iterable[dict[str, Any]],
    deleted_ids: set[str],
    feedbacks: Iterable[dict[str, Any]] = (),
) -> list[Finding]:
    """Transcripts whose attempt, turns, station or result did not arrive intact.

    Reasons: `user_not_imported`, `missing`, `station_not_imported`, `count_differs`, `no_result`.
    """
    lookups = await b2c_lookups.build(session)
    expected_by_ref: dict[str, tuple[dict[str, Any], int]] = {}
    findings: list[Finding] = []
    transcripts = list(transcripts)
    # Which transcripts the importer's own matching says were marked in the old app.
    marked_in_legacy = {
        legacy_ref_for(migrated)
        for migrated, _ in migrate_transcripts(transcripts, list(feedbacks), StepReport())
        if migrated.result is not None
    }
    for document in transcripts:
        collection = _text(document.get("_collection"))
        legacy_user = _text(document.get("user_id"))
        migrated = attempt_from_transcript(document, app_type=_text(document.get("app_type")) or "sca")
        reference = legacy_ref_for(migrated)
        legacy_id = reference or _text(document.get("id"))
        if legacy_user in deleted_ids:
            findings.append(Finding("attempts", legacy_id, collection, "deleted", expected=True))
        elif not reference:
            findings.append(Finding("attempts", legacy_id, collection, "no_reference"))
        else:
            expected_by_ref[reference] = (document, len(migrated.messages))
            if lookups.user(legacy_user) is None:
                findings.append(Finding("attempts", legacy_id, collection, "user_not_imported"))
    if not expected_by_ref:
        return findings

    stored = {
        legacy_ref: (attempt_id, station_version_id)
        for legacy_ref, attempt_id, station_version_id in (
            await session.execute(
                select(Attempt.legacy_ref, Attempt.id, Attempt.station_version_id).where(
                    Attempt.legacy_ref.in_(list(expected_by_ref))
                )
            )
        ).all()
    }
    attempt_ids = [attempt_id for attempt_id, _ in stored.values()]
    live_turns = dict(
        (
            await session.execute(
                select(TranscriptMessage.attempt_id, func.count())
                .where(TranscriptMessage.attempt_id.in_(attempt_ids))
                .group_by(TranscriptMessage.attempt_id)
            )
        ).all()
    )
    compacted_turns = dict(
        (
            await session.execute(
                select(Transcript.attempt_id, Transcript.message_count).where(
                    Transcript.attempt_id.in_(attempt_ids)
                )
            )
        ).all()
    )
    with_result = set(
        (
            await session.scalars(
                select(AssessmentResult.attempt_id).where(AssessmentResult.attempt_id.in_(attempt_ids))
            )
        ).all()
    )
    for reference, (document, legacy_turns) in expected_by_ref.items():
        collection = _text(document.get("_collection"))
        if reference not in stored:
            findings.append(Finding("attempts", reference, collection, "missing"))
            continue
        attempt_id, station_version_id = stored[reference]
        if station_version_id is None:
            findings.append(Finding("attempts", reference, collection, "station_not_imported"))
        database_turns = int(live_turns.get(attempt_id, 0)) + int(compacted_turns.get(attempt_id, 0) or 0)
        if database_turns != legacy_turns:
            findings.append(
                Finding(
                    "attempts",
                    reference,
                    collection,
                    "count_differs",
                    detail=f"legacy {legacy_turns}, database {database_turns}",
                )
            )
        if attempt_id not in with_result and (
            reference in marked_in_legacy or document.get("feedback") or document.get("feedback_id")
        ):
            findings.append(Finding("attempts", reference, collection, "no_result"))
    return findings


async def reconcile_payments(session: AsyncSession, documents: Iterable[dict[str, Any]]) -> list[Finding]:
    """Payments that are missing, or arrived without a plan, a grant link or an amount.

    Reasons: `missing`, `no_plan`, `no_grant_link`, `amount_zero`.
    """
    findings: list[Finding] = []
    wanted: dict[str, dict[str, Any]] = {}
    for document in documents:
        intent = _text(document.get("payment_intent_id"))
        if intent:
            wanted[intent] = document
        else:
            findings.append(
                Finding(
                    "payments", _text(document.get("id")), _text(document.get("_collection")), "no_intent_id"
                )
            )
    if not wanted:
        return findings
    stored = {
        intent: (plan_id, entitlement_id, amount, row_id)
        for intent, plan_id, entitlement_id, amount, row_id in (
            await session.execute(
                select(
                    Payment.stripe_payment_intent_id,
                    Payment.plan_id,
                    Payment.entitlement_id,
                    Payment.amount_total_pence,
                    Payment.id,
                ).where(Payment.stripe_payment_intent_id.in_(list(wanted)))
            )
        ).all()
    }
    for intent, document in wanted.items():
        legacy_id, collection = _text(document.get("id")), _text(document.get("_collection"))
        if intent not in stored:
            findings.append(Finding("payments", legacy_id, collection, "missing"))
            continue
        plan_id, entitlement_id, amount, _ = stored[intent]
        if plan_id is None:
            findings.append(Finding("payments", legacy_id, collection, "no_plan"))
        if entitlement_id is None:
            findings.append(Finding("payments", legacy_id, collection, "no_grant_link"))
        if not amount:
            findings.append(Finding("payments", legacy_id, collection, "amount_zero"))
    return findings


async def reconcile_grants(session: AsyncSession, user_documents: Iterable[dict[str, Any]]) -> list[Finding]:
    """Paid legacy users whose purchase grant is missing, open-ended or ends on a different day.

    Reasons: `no_grant`, `ends_at_null`, `ends_at_differs`.
    """
    lookups = await b2c_lookups.build(session)
    findings: list[Finding] = []
    for document in user_documents:
        if document.get("has_paid") is not True:
            continue
        legacy_id, collection = _text(document.get("id")), _text(document.get("_collection"))
        user_id = lookups.user(legacy_id)
        if user_id is None:
            continue  # already reported as a missing user
        legacy_end = parse_timestamp(document.get("plan_end_date"))
        grants = (
            await session.scalars(
                select(Entitlement).where(
                    Entitlement.user_id == user_id,
                    Entitlement.source == "purchase",
                    Entitlement.source_ref == "legacy-import",
                )
            )
        ).all()
        if not grants:
            findings.append(Finding("grants", legacy_id, collection, "no_grant"))
        elif any(grant.ends_at is None for grant in grants):
            findings.append(Finding("grants", legacy_id, collection, "ends_at_null"))
        elif legacy_end is not None and all(
            grant.ends_at.date() != legacy_end.date() for grant in grants if grant.ends_at is not None
        ):
            findings.append(
                Finding(
                    "grants",
                    legacy_id,
                    collection,
                    "ends_at_differs",
                    detail=f"legacy {legacy_end.date()}, database "
                    + ", ".join(str(grant.ends_at.date()) for grant in grants if grant.ends_at),
                )
            )
    return findings


async def data_quality_counts(session: AsyncSession) -> dict[str, int]:
    """Counts of rows that look wrong regardless of Firestore, to size the repairs."""
    from app.features.stations.models import Station

    async def count(statement: Any) -> int:
        """Run one count query."""
        return int(await session.scalar(statement) or 0)

    return {
        "stations_approved": await count(select(func.count()).select_from(Station).where(Station.approved)),
        "stations_not_approved": await count(
            select(func.count()).select_from(Station).where(~Station.approved)
        ),
        "users_without_activated_at": await count(
            select(func.count()).select_from(User).where(User.activated_at.is_(None))
        ),
        "attempts_without_station_version": await count(
            select(func.count())
            .select_from(Attempt)
            .where(Attempt.legacy_ref.is_not(None), Attempt.station_version_id.is_(None))
        ),
        "legacy_attempts_stuck_interaction_complete": await count(
            select(func.count())
            .select_from(Attempt)
            .where(
                Attempt.legacy_ref.is_not(None),
                Attempt.status == "interaction_complete",
                Attempt.failed_reason.is_(None),
                ~Attempt.id.in_(select(AssessmentResult.attempt_id)),
            )
        ),
        "purchase_grants_without_end": await count(
            select(func.count())
            .select_from(Entitlement)
            .where(
                Entitlement.source == "purchase",
                Entitlement.ends_at.is_(None),
                Entitlement.revoked_at.is_(None),
            )
        ),
        "payments_without_plan": await count(
            select(func.count()).select_from(Payment).where(Payment.plan_id.is_(None))
        ),
        "payments_without_grant_link": await count(
            select(func.count()).select_from(Payment).where(Payment.entitlement_id.is_(None))
        ),
    }


def summarise(findings: Iterable[Finding]) -> dict[str, Counter[str]]:
    """Per entity, how many findings of each reason (expected ones are prefixed `expected:`)."""
    table: dict[str, Counter[str]] = {}
    for finding in findings:
        label = f"expected:{finding.reason}" if finding.expected else finding.reason
        table.setdefault(finding.entity, Counter())[label] += 1
    return table


def defects(findings: Iterable[Finding]) -> list[Finding]:
    """Only the findings nobody meant to leave out."""
    return [finding for finding in findings if not finding.expected]
