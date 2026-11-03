"""The steps `scripts/import_b2c_all.py` runs, in order, one handler each.

The first five reuse the single-feature importers' own transforms and loaders
(`scripts/import_b2c_*.py`), so the all-in-one copy cannot drift from them. The
rest are the collections no importer covered. See `b2c_inventory` for which
collection feeds which step.
"""

from __future__ import annotations

import importlib.util
import re
from collections.abc import Awaitable, Callable
from pathlib import Path
from types import ModuleType
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.migration import (
    b2c_firestore,
    b2c_inventory,
    b2c_lookups,
    b2c_sync,
    link_templates,
    load_b2c_attempts,
    load_b2c_billing,
    load_b2c_misc,
    load_b2c_mocks,
)
from app.migration import load_b2c_attempt_extras as extras
from app.migration.b2c_lookups import StepReport
from app.migration.b2c_media_sources import stream_b2c_media_documents
from app.migration.b2c_social_sources import stream_b2c_community_documents, stream_b2c_marketplace_documents
from app.migration.b2c_station_sources import stream_b2c_station_documents
from app.migration.b2c_user_sources import stream_b2c_user_documents
from app.migration.load_community import load_community
from app.migration.load_legacy_b2c import load_legacy_payments, load_legacy_referrals
from app.migration.load_marketplace import load_marketplace_posts, load_peer_sessions
from app.migration.load_media import load_media
from app.migration.load_stations import load_stations
from app.migration.loader import load_users

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"

STEPS = list(b2c_inventory.COPIED)


def _script(name: str) -> ModuleType:
    """The single-feature importers' transforms, reused rather than copied."""
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


class Run:
    """One importer invocation's shared state: the Firestore client and attempts read so far.

    `raw_db` is set only by the nightly sync, where `db` returns just the pending documents and
    `raw_db` is the real client for steps that need the whole picture to join against (every
    transcript, to resolve a debrief to its attempt).
    """

    def __init__(self, db: Any, raw_db: Any = None) -> None:
        self.db = db
        self.raw_db = raw_db
        self.pairs: list[Any] = []  # attempts, for the steps that hang off them
        self.imported_pairs: list[Any] = []  # the (attempt, transcript) pairs the attempts step wrote
        self._context: dict[str, list[dict[str, Any]]] = {}

    @property
    def syncing(self) -> bool:
        """Whether this run copies only pending documents (the nightly sync)."""
        return self.raw_db is not None

    def _read_from(self, db: Any, step: str) -> list[dict[str, Any]]:
        """Every document from every collection this step owns, seed rows dropped, with progress printed."""
        docs: list[dict[str, Any]] = []
        for collection, exam in b2c_inventory.COPIED[step].items():
            documents, seeded = b2c_firestore.stream(db, collection, app_type=exam or None)
            docs.extend(documents)
            if documents or seeded:
                dropped = f" (+{seeded} demo rows dropped)" if seeded else ""
                print(f"    read {collection}: {len(documents)}{dropped}")  # noqa: T201
        return docs

    def read(self, step: str) -> list[dict[str, Any]]:
        """The step's documents: all of them, or only the pending ones when syncing."""
        return self._read_from(self.db, step)

    def context(self, step: str) -> list[dict[str, Any]]:
        """The step's documents in full, once, to join against. Not what gets written or recorded."""
        if step not in self._context:
            self._context[step] = self._read_from(self.raw_db or self.db, step)
        return self._context[step]

    def matching(self, docs: list[dict], collections: dict[str, str]) -> list[dict]:
        """The subset of `docs` that came from one of `collections` (e.g. only the transcript collections)."""
        return [document for document in docs if document.get("_collection") in collections.values()]


def _legacy(report: Any, extra: list[str]) -> StepReport:
    """A `LoadReport`'s non-zero lines, so a step does not print fifteen zero counters."""
    notes = [
        part
        for part in report.summary().split("; ")
        if not part.startswith("problems") and re.search(r"[1-9]", part)
    ]
    return StepReport(problems=[*extra, *report.problems], notes=notes)


async def _users(session: AsyncSession, run: Run) -> StepReport:
    """The `users` step: reuses `import_b2c_users`'s transform, then loads people, payments and referrals."""
    merged, grants, payments, referrals, problems = _script("import_b2c_users").prepare_import(
        stream_b2c_user_documents()
    )
    report, _ids, email_ids = await load_users(session, merged, grants)
    report = report.merge(await load_legacy_payments(session, payments, user_ids=email_ids))
    return _legacy(
        report.merge(await load_legacy_referrals(session, referrals, user_ids=email_ids)), problems
    )


async def _stations(session: AsyncSession, run: Run) -> StepReport:
    """The `stations` step: reuses `import_b2c_stations`'s transform, then loads the library."""
    migrated, problems = _script("import_b2c_stations").transform_documents(stream_b2c_station_documents())
    return _legacy((await load_stations(session, migrated))[0], problems)


async def _media(session: AsyncSession, run: Run) -> StepReport:
    """The `media` step: reuses `import_b2c_media`'s transform, then loads study material."""
    migrated, problems = _script("import_b2c_media").transform_documents(stream_b2c_media_documents())
    return _legacy(await load_media(session, migrated), problems)


async def _community(session: AsyncSession, run: Run) -> StepReport:
    """The `community` step: reuses `import_b2c_community`'s transform, then loads posts and likes."""
    migrated, problems = _script("import_b2c_community").transform_documents(stream_b2c_community_documents())
    return _legacy(await load_community(session, migrated), problems)


async def _marketplace(session: AsyncSession, run: Run) -> StepReport:
    """The `marketplace` step: reuses `import_b2c_marketplace`'s transform, then loads posts and sessions."""
    posts, sessions, problems = _script("import_b2c_marketplace").transform_documents(
        stream_b2c_marketplace_documents()
    )
    return _legacy(
        (await load_marketplace_posts(session, posts)).merge(await load_peer_sessions(session, sessions)),
        problems,
    )


async def _attempts(session: AsyncSession, run: Run) -> StepReport:
    """The `attempts` step: transcripts of deleted accounts are dropped, the rest loaded with feedback."""
    docs = run.read("attempts")
    if run.syncing:
        if not docs:
            return StepReport()
        docs = b2c_sync.attempt_inputs(docs, run.context("attempts"))
    deleted = b2c_firestore.deleted_user_ids(run.db)
    kept = [document for document in docs if str(document.get("user_id") or "") not in deleted]
    transcripts = run.matching(kept, b2c_inventory.TRANSCRIPT_COLLECTIONS)
    feedbacks = run.matching(kept, b2c_inventory.FEEDBACK_COLLECTIONS)
    report, pairs = await load_b2c_attempts.load(
        session, transcripts, feedbacks, await b2c_lookups.build(session)
    )
    run.imported_pairs = pairs
    # Syncing imported only some transcripts, so later steps rebuild the full picture themselves.
    run.pairs = [] if run.syncing else pairs
    dropped = run.matching(docs, b2c_inventory.TRANSCRIPT_COLLECTIONS)
    report.count("transcripts of deleted accounts (not copied)", len(dropped) - len(transcripts))
    return report


async def _needs_attempts(run: Run) -> None:
    """`--only debriefs` without `attempts`: read the transcripts just to resolve keys."""
    if not run.pairs:
        docs = run.context("attempts")
        run.pairs = load_b2c_attempts.migrate_transcripts(
            run.matching(docs, b2c_inventory.TRANSCRIPT_COLLECTIONS), [], StepReport()
        )


async def _live_coverage(session: AsyncSession, run: Run) -> StepReport:
    """The `live_coverage` step: attaches saved live-marking snapshots to their already-copied attempts."""
    await _needs_attempts(run)
    return await extras.load_live_coverage(session, run.read("live_coverage"), run.pairs)


async def _debriefs(session: AsyncSession, run: Run) -> StepReport:
    """The `debriefs` step: attaches tutor debrief summaries to their already-copied attempts."""
    await _needs_attempts(run)
    return await extras.load_debriefs(
        session, run.read("debriefs"), run.pairs, await b2c_lookups.build(session)
    )


async def _mocks(session: AsyncSession, run: Run) -> StepReport:
    """The `mocks` step: builds station sets, then hangs each already-copied attempt on its slot."""
    mocks = run.read("mocks")
    deleted = b2c_firestore.deleted_user_ids(run.db)
    if run.syncing:
        if not mocks and not run.imported_pairs:
            return StepReport()
        # New transcripts link to mocks copied long ago, and a changed mock re-links its old ones.
        changed = {str(document["id"]) for document in mocks}
        transcripts = [raw for _attempt, raw in run.imported_pairs]
        imported = {(raw["_collection"], raw["id"]) for raw in transcripts}
        transcripts += [
            document
            for document in run.matching(run.context("attempts"), b2c_inventory.TRANSCRIPT_COLLECTIONS)
            if str(document.get("mock_id") or "") in changed
            and (document["_collection"], document["id"]) not in imported
        ]
        linkable_mocks = run.context("mocks")
    else:
        docs = run.matching(run.read("attempts"), b2c_inventory.TRANSCRIPT_COLLECTIONS)
        transcripts = docs
        linkable_mocks = mocks
    transcripts = [document for document in transcripts if str(document.get("user_id") or "") not in deleted]
    lookups = await b2c_lookups.build(session)
    report = await load_b2c_mocks.load_mocks(session, mocks, lookups)
    report.merge(
        await load_b2c_mocks.link_attempts_to_sessions(session, linkable_mocks, transcripts, lookups)
    )
    return report


async def _with_lookups(
    session: AsyncSession, run: Run, step: str, handler: Callable[..., Awaitable[StepReport]]
) -> StepReport:
    """Run a step's handler with the documents it owns plus a freshly built `Lookups`."""
    return await handler(session, run.read(step), await b2c_lookups.build(session))


async def _partners(session: AsyncSession, run: Run) -> StepReport:
    """The `partners` step: loads partner arrivals and reporters, split from one read by collection."""
    docs = run.read("partners")
    return await load_b2c_billing.load_partners(
        session,
        run.matching(docs, {"a": b2c_inventory.PARTNER_ARRIVAL_COLLECTION}),
        run.matching(docs, {"r": b2c_inventory.PARTNER_REPORTER_COLLECTION}),
    )


async def _peer_practice(session: AsyncSession, run: Run) -> StepReport:
    """The `peer_practice` step: loads human peer-practice sessions with their matched feedback."""
    docs = run.read("peer_practice")
    return await load_b2c_misc.load_peer_practice(
        session,
        run.matching(docs, b2c_inventory.HUMAN_PRACTICE_SESSION_COLLECTIONS),
        run.matching(docs, b2c_inventory.HUMAN_PRACTICE_FEEDBACK_COLLECTIONS),
        await b2c_lookups.build(session),
    )


HANDLERS: dict[str, Callable[[AsyncSession, Run], Awaitable[StepReport]]] = {
    "users": _users,
    "stations": _stations,
    "templates": lambda session, run: link_templates.bind_unbound_versions(session),
    "media": _media,
    "community": _community,
    "marketplace": _marketplace,
    "attempts": _attempts,
    "mocks": _mocks,
    "live_coverage": _live_coverage,
    "debriefs": _debriefs,
    "partners": _partners,
    "peer_practice": _peer_practice,
    "payments": lambda session, run: _with_lookups(session, run, "payments", load_b2c_billing.load_payments),
    "referrals": lambda session, run: _with_lookups(
        session, run, "referrals", load_b2c_billing.load_referrals
    ),
    "cvs": lambda session, run: _with_lookups(session, run, "cvs", load_b2c_misc.load_cvs),
    "site_messages": lambda session, run: _with_lookups(
        session, run, "site_messages", load_b2c_misc.load_site_messages
    ),
}
