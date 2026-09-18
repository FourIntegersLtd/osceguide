"""Answering the tutor's tool calls.

Every answer is prose, because the model reads it out. Where there is also
something to put on screen, `display` travels beside it and the worker
publishes it on the data channel unchanged — the backend never composes a
route, because which screen a thing lives on is the frontend's business.

Nothing here tells the tutor about material this person cannot open. A refusal
that names a locked title is an advertisement, and the tutor would then be
talking about something the doctor cannot reach.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog import service as catalog
from app.features.entitlements import service as entitlements
from app.features.stations import service_reads as stations
from app.features.tutor_memory import domain, errors, repository, tools_catalog
from app.features.tutor_memory.schemas import ToolResult

CARD_SCHEMA_VERSION = 2

NOTHING_FOUND = "You have nothing on file about that. Say so plainly rather than guessing."
NOT_CONFIGURED = (
    "The material search is not available in this deployment. Say you cannot look that up "
    "right now, and answer from what you already know or offer to come back to it."
)


async def tool_hook(
    session: AsyncSession,
    *,
    tool: str,
    arguments: dict[str, Any],
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    now: datetime,
) -> dict[str, Any]:
    """The seam `assistant` calls, once it has established whose session this is.

    Returns a plain dict because the seam is typed in `assistant`, which sits
    below this slice and cannot name this slice's schemas.
    """
    result = await run(
        session,
        tool=tool,
        arguments=arguments,
        user_id=user_id,
        session_id=session_id,
        now=now,
    )
    return result.model_dump()


async def run(
    session: AsyncSession,
    *,
    tool: str,
    arguments: dict[str, Any],
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    now: datetime,
) -> ToolResult:
    """Dispatch one call, having first checked it against its own schema."""
    schema = tools_catalog.schema_for(tool)
    if schema is None:
        raise errors.UnknownTool(f"No tool named {tool!r}.")
    try:
        cleaned = domain.validate_tool_arguments(schema, arguments)
    except domain.InvalidToolArguments as exc:
        raise errors.ToolArgumentsInvalid(str(exc)) from exc

    if tool == tools_catalog.RECALL_HISTORY:
        return await _recall(session, user_id=user_id, now=now, **_recall_args(cleaned))
    if tool == tools_catalog.SEARCH_MATERIAL:
        return ToolResult(result=NOT_CONFIGURED)
    if tool == tools_catalog.SUGGEST_MATERIAL:
        return await _suggest(session, user_id=user_id, now=now, **_suggest_args(cleaned))
    return await _remember(session, user_id=user_id, session_id=session_id, fact=str(cleaned["fact"]))


def _recall_args(cleaned: dict[str, Any]) -> dict[str, Any]:
    return {
        "query": str(cleaned.get("query") or ""),
        "kind": str(cleaned.get("kind") or "any"),
        "limit": int(cleaned.get("limit") or 3),
    }


def _suggest_args(cleaned: dict[str, Any]) -> dict[str, Any]:
    return {"ref": str(cleaned.get("ref") or ""), "reason": str(cleaned.get("reason") or "")}


async def _recall(
    session: AsyncSession, *, user_id: uuid.UUID, query: str, kind: str, limit: int, now: datetime
) -> ToolResult:
    """Search this person's own past by the words they used.

    Substring matching over their own small history rather than a search index:
    a doctor has tens of these, not thousands, and a semantic index over
    somebody's private record is a great deal of machinery for a list that fits
    on a screen.
    """
    lines: list[str] = []
    needle = query.lower()

    if kind in {"note", "any"}:
        for note in await repository.notes_of_kind(session, user_id, kind="stated_fact", limit=20):
            fact = str((note.body or {}).get("fact") or "")
            if needle in fact.lower():
                lines.append(f"They told you: {fact}")

    if kind in {"debrief", "consultation", "any"}:
        for row in await repository.recent_debrief_summaries(session, user_id, limit=20):
            haystack = " ".join(
                [str(row.narrative or ""), *[str(i) for i in (row.key_insights or [])]]
            ).lower()
            if needle not in haystack:
                continue
            steps = domain.open_action_items([row.action_plan or []])
            when = domain.days_ago(row.created_at, now)
            agreed = f" You agreed they would: {'; '.join(steps)}." if steps else ""
            lines.append(f"A debrief {when} days ago: {row.narrative or 'no narrative'}.{agreed}")

    if kind in {"activity", "any"}:
        for event in await repository.recent_events(session, user_id, limit=40):
            if needle in event.title.lower():
                lines.append(
                    f"They {event.kind} {event.title}, {domain.days_ago(event.occurred_at, now)} days ago."
                )

    if not lines:
        return ToolResult(result=NOTHING_FOUND)
    return ToolResult(result=" ".join(lines[:limit]))


async def _suggest(
    session: AsyncSession, *, user_id: uuid.UUID, ref: str, reason: str, now: datetime
) -> ToolResult:
    """Put one station on the doctor's screen, if they may open it.

    Only stations for now: they are the one kind whose entitlement this backend
    can decide, and suggesting something a doctor cannot open is worse than
    suggesting nothing.
    """
    try:
        version_id = uuid.UUID(ref)
    except ValueError:
        return ToolResult(result=_cannot_suggest())

    summaries = await stations.summaries_by_version_id(session, None, [version_id])
    summary = summaries.get(version_id)
    if summary is None:
        return ToolResult(result=_cannot_suggest())

    allowed = await _may_open(session, user_id=user_id, version_id=version_id, now=now)
    if not allowed:
        return ToolResult(result=_cannot_suggest())

    return ToolResult(
        result=(
            f"Done — {summary.title} is on their screen now. Tell them in one sentence why you "
            "chose it, in your own words."
        ),
        display={
            "type": "assistant_card",
            "schemaVersion": CARD_SCHEMA_VERSION,
            "card": "suggestion",
            "ref": {"kind": "station", "id": str(version_id), "slug": None},
            "title": summary.title,
            "reason": reason,
        },
    )


def _cannot_suggest() -> str:
    """Deliberately says nothing about what was refused or why.

    Naming the title would tell the doctor about something they cannot open,
    and naming the reason ("you have not paid for that exam") would have the
    tutor delivering a billing message mid-conversation.
    """
    return (
        "You could not put that on their screen. Say you will follow it up rather than "
        "explaining why, and carry on."
    )


LIBRARY_PAGE = 200


async def _may_open(
    session: AsyncSession, *, user_id: uuid.UUID, version_id: uuid.UUID, now: datetime
) -> bool:
    """Whether this station is in the library of an exam they hold.

    Asked per entitled exam rather than over the whole library, because the
    question is "may they open this?" and an exam they do not hold is not a
    smaller answer — it is a different one.
    """
    grants = await entitlements.list_for_user(session, user_id, now=now)
    entitled = domain.entitled_exam_ids(grants)
    codes = {ref.id: ref.code for ref in await catalog.exam_refs(session)}
    for exam_id in entitled:
        code = codes.get(exam_id)
        if code is None:
            continue
        library, _ = await stations.browse_library(session, exam_code=code, limit=LIBRARY_PAGE, cursor=None)
        if any(row.version_id == version_id for row in library):
            return True
    return False


async def _remember(
    session: AsyncSession, *, user_id: uuid.UUID, session_id: uuid.UUID, fact: str
) -> ToolResult:
    clipped = domain.clip_fact(fact)
    if not clipped:
        return ToolResult(result="There was nothing to write down. Carry on.")
    await repository.add_note(
        session,
        user_id=user_id,
        exam_id=None,
        session_id=session_id,
        kind="stated_fact",
        body={"fact": clipped},
    )
    return ToolResult(result="Noted. Do not read it back to them; just carry on.")
