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
    load_b2c_attempts,
    load_b2c_billing,
    load_b2c_misc,
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
    def __init__(self, db: Any) -> None:
        self.db = db
        self.pairs: list[Any] = []  # attempts, for the steps that hang off them

    def read(self, step: str) -> list[dict[str, Any]]:
        docs: list[dict[str, Any]] = []
        for collection, exam in b2c_inventory.COPIED[step].items():
            rows, seeded = b2c_firestore.stream(self.db, collection, app_type=exam or None)
            docs.extend(rows)
            if rows or seeded:
                dropped = f" (+{seeded} demo rows dropped)" if seeded else ""
                print(f"    read {collection}: {len(rows)}{dropped}")  # noqa: T201
        return docs

    def of(self, docs: list[dict], collections: dict[str, str]) -> list[dict]:
        return [d for d in docs if d.get("_collection") in collections.values()]


def _legacy(report: Any, extra: list[str]) -> StepReport:
    """A `LoadReport`'s non-zero lines, so a step does not print fifteen zero counters."""
    notes = [
        part
        for part in report.summary().split("; ")
        if not part.startswith("problems") and re.search(r"[1-9]", part)
    ]
    return StepReport(problems=[*extra, *report.problems], notes=notes)


async def _users(s: AsyncSession, run: Run) -> StepReport:
    merged, grants, payments, referrals, problems = _script("import_b2c_users").prepare_import(
        stream_b2c_user_documents()
    )
    report, _ids, email_ids = await load_users(s, merged, grants)
    report = report.merge(await load_legacy_payments(s, payments, user_ids=email_ids))
    return _legacy(report.merge(await load_legacy_referrals(s, referrals, user_ids=email_ids)), problems)


async def _stations(s: AsyncSession, run: Run) -> StepReport:
    migrated, problems = _script("import_b2c_stations").transform_documents(stream_b2c_station_documents())
    return _legacy((await load_stations(s, migrated))[0], problems)


async def _media(s: AsyncSession, run: Run) -> StepReport:
    migrated, problems = _script("import_b2c_media").transform_documents(stream_b2c_media_documents())
    return _legacy(await load_media(s, migrated), problems)


async def _community(s: AsyncSession, run: Run) -> StepReport:
    migrated, problems = _script("import_b2c_community").transform_documents(stream_b2c_community_documents())
    return _legacy(await load_community(s, migrated), problems)


async def _marketplace(s: AsyncSession, run: Run) -> StepReport:
    posts, sessions, problems = _script("import_b2c_marketplace").transform_documents(
        stream_b2c_marketplace_documents()
    )
    return _legacy(
        (await load_marketplace_posts(s, posts)).merge(await load_peer_sessions(s, sessions)), problems
    )


async def _attempts(s: AsyncSession, run: Run) -> StepReport:
    docs = run.read("attempts")
    deleted = b2c_firestore.deleted_user_ids(run.db)
    kept = [d for d in docs if str(d.get("user_id") or "") not in deleted]
    transcripts = run.of(kept, b2c_inventory.TRANSCRIPT_COLLECTIONS)
    feedbacks = run.of(kept, b2c_inventory.FEEDBACK_COLLECTIONS)
    report, run.pairs = await load_b2c_attempts.load(s, transcripts, feedbacks, await b2c_lookups.build(s))
    dropped = run.of(docs, b2c_inventory.TRANSCRIPT_COLLECTIONS)
    report.count("transcripts of deleted accounts (not copied)", len(dropped) - len(transcripts))
    return report


async def _needs_attempts(run: Run) -> None:
    """`--only debriefs` without `attempts`: read the transcripts just to resolve keys."""
    if not run.pairs:
        docs = run.read("attempts")
        run.pairs = load_b2c_attempts.migrate_transcripts(
            run.of(docs, b2c_inventory.TRANSCRIPT_COLLECTIONS), [], StepReport()
        )


async def _live_coverage(s: AsyncSession, run: Run) -> StepReport:
    await _needs_attempts(run)
    return await extras.load_live_coverage(s, run.read("live_coverage"), run.pairs)


async def _debriefs(s: AsyncSession, run: Run) -> StepReport:
    await _needs_attempts(run)
    return await extras.load_debriefs(s, run.read("debriefs"), run.pairs, await b2c_lookups.build(s))


async def _with_lookups(
    s: AsyncSession, run: Run, step: str, fn: Callable[..., Awaitable[StepReport]]
) -> StepReport:
    return await fn(s, run.read(step), await b2c_lookups.build(s))


async def _partners(s: AsyncSession, run: Run) -> StepReport:
    docs = run.read("partners")
    return await load_b2c_billing.load_partners(
        s,
        run.of(docs, {"a": b2c_inventory.PARTNER_ARRIVAL_COLLECTION}),
        run.of(docs, {"r": b2c_inventory.PARTNER_REPORTER_COLLECTION}),
    )


async def _peer_practice(s: AsyncSession, run: Run) -> StepReport:
    docs = run.read("peer_practice")
    return await load_b2c_misc.load_peer_practice(
        s,
        run.of(docs, b2c_inventory.HUMAN_PRACTICE_SESSION_COLLECTIONS),
        run.of(docs, b2c_inventory.HUMAN_PRACTICE_FEEDBACK_COLLECTIONS),
        await b2c_lookups.build(s),
    )


HANDLERS: dict[str, Callable[[AsyncSession, Run], Awaitable[StepReport]]] = {
    "users": _users,
    "stations": _stations,
    "media": _media,
    "community": _community,
    "marketplace": _marketplace,
    "attempts": _attempts,
    "live_coverage": _live_coverage,
    "debriefs": _debriefs,
    "partners": _partners,
    "peer_practice": _peer_practice,
    "payments": lambda s, r: _with_lookups(s, r, "payments", load_b2c_billing.load_payments),
    "referrals": lambda s, r: _with_lookups(s, r, "referrals", load_b2c_billing.load_referrals),
    "cvs": lambda s, r: _with_lookups(s, r, "cvs", load_b2c_misc.load_cvs),
    "site_messages": lambda s, r: _with_lookups(s, r, "site_messages", load_b2c_misc.load_site_messages),
}
