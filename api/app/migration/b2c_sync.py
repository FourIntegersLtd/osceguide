"""Copy only what is new or changed in the legacy Firestore since the last run.

`import_b2c_all.py` re-reads every document of every collection and relies on the database to
skip what it already has. This module is the cheaper, safer path the nightly sync uses:

1. **List** every collection as `{document id: last-changed time}`. Ids and times only: no
   document body is downloaded.
2. **Subtract** the ledger (`legacy_sync_records`): a document recorded at the same time is
   already copied and is never touched again, so a row someone later edited or deleted on the
   new platform is not brought back.
3. **Fetch** only the remaining documents, by id (`PendingClient`). The existing step handlers
   see a Firestore that appears to hold just those documents.
4. **Record** them in the ledger once their step finished. A record the old site holds that cannot
   be copied as it stands is reported once and recorded too; a step that crashes is rolled back
   and records nothing, so its documents are tried again next run (the loaders are add-only, so
   trying again never duplicates).

A document edited in Firestore after it was copied has a newer time than its ledger row, so it
is fetched again: that is how a user who has just bought a plan reaches the new platform.

Documents changed within the last `SETTLE_WINDOW` are left for the next run, so a consultation
still in progress is not copied half finished.

Firestore is only read, never written.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import Base
from app.features.health.models import LegacySyncRecord
from app.migration import b2c_firestore, b2c_inventory
from app.migration.load_b2c_attempts import practice_key

SETTLE_WINDOW = timedelta(minutes=30)
FETCH_CHUNK = 300  # documents fetched per Firestore round trip
RECORD_CHUNK = 2000  # ledger rows written per statement


@dataclass(frozen=True)
class CollectionPlan:
    """What the comparison found in one Firestore collection."""

    collection: str
    in_firestore: int
    already_copied: int
    pending: int
    settling: int


def copied_collections() -> list[str]:
    """Every Firestore collection some step copies, in step order."""
    return [name for collections in b2c_inventory.COPIED.values() for name in collections]


def list_versions(db: Any, collection: str) -> dict[str, datetime]:
    """`{document id: Firestore update_time}` for a collection, without downloading any field."""
    return {snapshot.id: snapshot.update_time for snapshot in db.collection(collection).select([]).stream()}


async def ledger_exists(session: AsyncSession) -> bool:
    """Whether the ledger table has been migrated into this database."""
    return bool(await session.scalar(select(func.to_regclass(LegacySyncRecord.__tablename__))))


async def create_ledger(session: AsyncSession) -> None:
    """Create the ledger table inside the open transaction (a preview rolls it back)."""
    await session.run_sync(lambda sync_session: LegacySyncRecord.__table__.create(sync_session.connection()))


def baseline_rows(
    db: Any, ledger: dict[str, dict[str, datetime]], cutoff: datetime
) -> dict[tuple[str, str], datetime]:
    """Documents the earlier full import already covered: unrecorded and last changed before `cutoff`.

    Used once, to start the ledger from a known import without running the loaders over every
    document again. Anything changed on or after `cutoff` is left for the sync to copy.
    """
    existing = set(b2c_firestore.root_collection_names(db))
    rows: dict[tuple[str, str], datetime] = {}
    for collection in copied_collections():
        if collection not in existing:
            continue
        copied = ledger.get(collection, {})
        for doc_id, updated_at in list_versions(db, collection).items():
            if doc_id not in copied and updated_at < cutoff:
                rows[(collection, doc_id)] = updated_at
    return rows


async def load_ledger(session: AsyncSession) -> dict[str, dict[str, datetime]]:
    """Everything the sync has recorded, as `{collection: {document id: time copied at}}`."""
    ledger: dict[str, dict[str, datetime]] = {}
    rows = await session.execute(
        select(LegacySyncRecord.collection, LegacySyncRecord.doc_id, LegacySyncRecord.source_updated_at)
    )
    for collection, doc_id, updated_at in rows.all():
        ledger.setdefault(collection, {})[doc_id] = updated_at
    return ledger


def plan_pending(
    db: Any,
    ledger: dict[str, dict[str, datetime]],
    *,
    now: datetime,
    settle: timedelta = SETTLE_WINDOW,
) -> tuple[dict[str, dict[str, datetime]], list[CollectionPlan]]:
    """Compare Firestore with the ledger: the pending `{collection: {id: time}}` and a row per collection."""
    existing = set(b2c_firestore.root_collection_names(db))
    pending: dict[str, dict[str, datetime]] = {}
    plans: list[CollectionPlan] = []
    for collection in copied_collections():
        versions = list_versions(db, collection) if collection in existing else {}
        copied = ledger.get(collection, {})
        pending[collection] = {}
        settling = 0
        for doc_id, updated_at in versions.items():
            recorded = copied.get(doc_id)
            if recorded is not None and updated_at <= recorded:
                continue
            if now - updated_at < settle:
                settling += 1
                continue
            pending[collection][doc_id] = updated_at
        plans.append(
            CollectionPlan(
                collection=collection,
                in_firestore=len(versions),
                already_copied=sum(1 for doc_id in versions if doc_id in copied),
                pending=len(pending[collection]),
                settling=settling,
            )
        )
    return pending, plans


class _PendingCollection:
    """One collection as the step handlers see it: `stream()` yields only the pending documents."""

    def __init__(self, owner: PendingClient, name: str) -> None:
        self._owner = owner
        self._name = name

    def stream(self) -> Iterator[Any]:
        """Fetch the pending documents by id, in chunks, and remember each as served."""
        owner = self._owner
        if self._name not in owner.pending:
            raise RuntimeError(
                f"{self._name} was not in the sync plan; add its step to app/migration/b2c_inventory.py"
            )
        wanted = owner.pending[self._name]
        raw_collection = owner.raw.collection(self._name)
        ids = sorted(wanted)
        for start in range(0, len(ids), FETCH_CHUNK):
            references = [raw_collection.document(doc_id) for doc_id in ids[start : start + FETCH_CHUNK]]
            for snapshot in owner.raw.get_all(references):
                if not snapshot.exists:
                    continue
                # The time recorded is the one listed BEFORE fetching: if the document changes in
                # between, the ledger is older than Firestore and the next run fetches it again.
                owner.served[(self._name, snapshot.id)] = wanted[snapshot.id]
                yield snapshot

    def __getattr__(self, attribute: str) -> Any:
        """Everything but `stream()` (select, count, document) goes straight to Firestore."""
        return getattr(self._owner.raw.collection(self._name), attribute)


class PendingClient:
    """A Firestore client that only ever returns the documents still to be copied."""

    def __init__(self, raw: Any, pending: dict[str, dict[str, datetime]]) -> None:
        self.raw = raw
        self.pending = pending
        self.served: dict[tuple[str, str], datetime] = {}

    def collection(self, name: str) -> _PendingCollection:
        """The named collection, filtered to its pending documents."""
        return _PendingCollection(self, name)

    def collections(self) -> Any:
        """The real list of root collections (the inventory check needs every name)."""
        return self.raw.collections()

    def take_served(self, collections: set[str]) -> dict[tuple[str, str], datetime]:
        """Hand over, and forget, the documents served from these collections since the last call."""
        taken = {key: value for key, value in self.served.items() if key[0] in collections}
        for key in taken:
            del self.served[key]
        return taken


async def record(session: AsyncSession, served: dict[tuple[str, str], datetime]) -> int:
    """Write the ledger rows for documents a step has fully copied; returns how many."""
    rows = [
        {"collection": collection, "doc_id": doc_id, "source_updated_at": updated_at}
        for (collection, doc_id), updated_at in served.items()
    ]
    for start in range(0, len(rows), RECORD_CHUNK):
        statement = insert(LegacySyncRecord).values(rows[start : start + RECORD_CHUNK])
        await session.execute(
            statement.on_conflict_do_update(
                index_elements=[LegacySyncRecord.collection, LegacySyncRecord.doc_id],
                set_={"source_updated_at": statement.excluded.source_updated_at, "updated_at": func.now()},
            )
        )
    return len(rows)


async def table_counts(session: AsyncSession) -> dict[str, int]:
    """Row count of every table, so a run can say how many rows each one gained."""
    counts: dict[str, int] = {}
    for table in Base.metadata.sorted_tables:
        if table.name == LegacySyncRecord.__tablename__:
            continue
        counts[table.name] = int(await session.scalar(select(func.count()).select_from(table)) or 0)
    return counts


def steps_with_work(plans: list[CollectionPlan]) -> set[str]:
    """Steps that have pending documents, plus the steps that must follow them.

    New stations need their template bound; new transcripts need linking to their mock session.
    """
    pending = {plan.collection for plan in plans if plan.pending}
    steps = {step for step, collections in b2c_inventory.COPIED.items() if pending & set(collections)}
    if "stations" in steps:
        steps.add("templates")
    if "attempts" in steps:
        steps.add("mocks")
    return steps


def attempt_inputs(
    pending_docs: list[dict[str, Any]], context_docs: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """The transcripts and feedback to import for an attempts run, joined against everything.

    A feedback document can arrive after its transcript was copied (the mark lands later), and a
    transcript is matched to its feedback by attempt id or by (user, mock, station). So the
    transcripts imported are the pending ones plus any whose feedback is pending, and the
    feedback passed along is just what belongs to them.
    """
    pending_ids = {(doc["_collection"], doc["id"]) for doc in pending_docs}
    transcript_collections = set(b2c_inventory.TRANSCRIPT_COLLECTIONS.values())
    feedback_collections = set(b2c_inventory.FEEDBACK_COLLECTIONS.values())

    def attempt_key(doc: dict[str, Any]) -> tuple[str, str]:
        return (str(doc.get("app_type") or ""), str(doc.get("attempt_id") or ""))

    pending_feedback = [doc for doc in pending_docs if doc["_collection"] in feedback_collections]
    feedback_attempts = {attempt_key(doc) for doc in pending_feedback if doc.get("attempt_id")}
    # (exam, user, mock, station) only identifies a practice run when none of its parts is blank.
    feedback_practice = {practice_key(doc) for doc in pending_feedback if all(practice_key(doc))}
    transcripts = [
        doc
        for doc in context_docs
        if doc["_collection"] in transcript_collections
        and (
            (doc["_collection"], doc["id"]) in pending_ids
            or attempt_key(doc) in feedback_attempts
            or practice_key(doc) in feedback_practice
        )
    ]
    imported_attempts = {attempt_key(doc) for doc in transcripts}
    imported_practice = {practice_key(doc) for doc in transcripts}
    feedback = [
        doc
        for doc in context_docs
        if doc["_collection"] in feedback_collections
        and (attempt_key(doc) in imported_attempts or practice_key(doc) in imported_practice)
    ]
    return [*transcripts, *feedback]


def now_utc() -> datetime:
    """The current time, timezone-aware, so it compares with Firestore's `update_time`."""
    return datetime.now(UTC)
