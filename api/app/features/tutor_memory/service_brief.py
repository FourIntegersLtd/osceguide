"""Composing what the tutor is told about one learner before it speaks.

The brief is a plain dict; its shape is the engine's
(`osce_assessment.prompts._tutor_brief`), and every fact in it is read back out
of this person's own records. Nothing is invented here, because the prompt
forbids the tutor from saying anything the brief does not carry.

Read through other slices' services, never their tables: the consultations come
from `attempts`, the station titles from `stations`, the exam codes from
`catalog`, and only the notes, events and debrief summaries are ours.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import service_reads as attempts
from app.features.stations import service_reads as stations
from app.features.tutor_memory import domain, repository
from app.features.tutor_memory.tools_catalog import TOOL_ROLES

RECENT_ATTEMPTS = 12
MAX_CONSULTATIONS = 6
MAX_DEBRIEFS = 3
MAX_FACTS = 5
MAX_ACTIVITY = 8


async def compose(session: AsyncSession, *, user_id: uuid.UUID, now: datetime) -> dict[str, Any]:
    """Everything the tutor remembers about this person, in the engine's shape."""
    refs = await attempts.recent_for_user(session, user_id, limit=RECENT_ATTEMPTS)
    titles = await _titles(session, refs)

    return {
        "consultations": await _consultations(session, user_id, refs, titles, now=now),
        "debriefs": await _debriefs(session, user_id, refs, titles, now=now),
        "last_conversation": await _last_conversation(session, user_id, now=now),
        "facts": await _facts(session, user_id),
        "activity": await _activity(session, user_id, now=now),
        "tool_names": dict(TOOL_ROLES),
    }


async def _titles(session: AsyncSession, refs: list[attempts.AttemptRef]) -> dict[uuid.UUID, str]:
    version_ids = [r.station_version_id for r in refs if r.station_version_id]
    summaries = await stations.summaries_by_version_id(session, None, version_ids)
    return {version_id: summary.title for version_id, summary in summaries.items()}


def _title_of(ref: attempts.AttemptRef, titles: dict[uuid.UUID, str]) -> str:
    return titles.get(ref.station_version_id or uuid.UUID(int=0)) or "a consultation"


async def _consultations(
    session: AsyncSession,
    user_id: uuid.UUID,
    refs: list[attempts.AttemptRef],
    titles: dict[uuid.UUID, str],
    *,
    now: datetime,
) -> list[dict[str, Any]]:
    """The marked consultations, most recent first, as observations rather than scores.

    Only the ones that were marked: a consultation with no result is one the
    tutor knows nothing about beyond that it happened, and saying "how did that
    go?" about it invites an answer the tutor cannot check.
    """
    out: list[dict[str, Any]] = []
    for ref in refs:
        if ref.kind == "debrief" or not ref.has_result:
            continue
        results = await attempts.read_results(session, ref.id, requester_id=user_id, is_admin=False)
        if not results:
            continue
        item = domain.observations_from_result(results[0].payload)
        item["title"] = _title_of(ref, titles)
        item["days_ago"] = domain.days_ago(ref.completed_at or ref.created_at, now)
        out.append(item)
        if len(out) == MAX_CONSULTATIONS:
            break
    return out


async def _debriefs(
    session: AsyncSession,
    user_id: uuid.UUID,
    refs: list[attempts.AttemptRef],
    titles: dict[uuid.UUID, str],
    *,
    now: datetime,
) -> list[dict[str, Any]]:
    by_id = {r.id: r for r in refs}
    out: list[dict[str, Any]] = []
    for row in await repository.recent_debrief_summaries(session, user_id, limit=MAX_DEBRIEFS):
        ref = by_id.get(row.attempt_id)
        out.append(
            {
                "title": _title_of(ref, titles) if ref else "a consultation",
                "days_ago": domain.days_ago(row.created_at, now),
                "insights": list(row.key_insights or []),
                "agreed_steps": list(row.action_plan or []),
            }
        )
    return out


async def _last_conversation(
    session: AsyncSession, user_id: uuid.UUID, *, now: datetime
) -> dict[str, Any] | None:
    notes = await repository.notes_of_kind(session, user_id, kind="session_summary", limit=1)
    if not notes:
        return None
    body = notes[0].body or {}
    return {
        "days_ago": domain.days_ago(notes[0].created_at, now),
        "summary": str(body.get("summary") or ""),
        "agreed_next_steps": domain.open_action_items([body.get("agreed_next_steps") or []]),
    }


async def _facts(session: AsyncSession, user_id: uuid.UUID) -> list[str]:
    notes = await repository.notes_of_kind(session, user_id, kind="stated_fact", limit=MAX_FACTS)
    return [str((n.body or {}).get("fact") or "") for n in notes if (n.body or {}).get("fact")]


async def _activity(session: AsyncSession, user_id: uuid.UUID, *, now: datetime) -> list[dict[str, Any]]:
    rows = await repository.recent_events(session, user_id, limit=MAX_ACTIVITY)
    return [
        {"kind": row.kind, "title": row.title, "days_ago": domain.days_ago(row.occurred_at, now)}
        for row in rows
    ]
