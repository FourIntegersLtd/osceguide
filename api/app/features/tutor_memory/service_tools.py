"""Answering the tutor's tool calls.

Every answer is prose, because the model reads it out. Where there is also something to
put on screen, `display` travels beside it and the worker publishes it unchanged.

Nothing here tells the tutor about material this person cannot open — a refusal that names
a locked title is an advertisement.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ports import MaterialIndex
from app.features.catalog import service as catalog
from app.features.entitlements import service as entitlements
from app.features.stations import service_library_reads as library_reads
from app.features.stations import service_reads as stations
from app.features.tutor_memory import (
    action_plan,
    domain,
    errors,
    repository,
    service_recall,
    service_search,
    tools_catalog,
)
from app.features.tutor_memory.index import build_material_index
from app.features.tutor_memory.schemas import ToolResult

NOTHING_FOUND = "You have nothing on file about that. Say so plainly rather than guessing."


async def tool_hook(
    session: AsyncSession,
    *,
    tool: str,
    arguments: dict[str, Any],
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    now: datetime,
) -> dict[str, Any]:
    """What `assistant` calls, once it has established whose session this is.

    Returns a plain dict: it goes straight back to the worker as JSON.
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
    index: MaterialIndex | None = None,
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
        return await service_recall.recall(session, user_id=user_id, now=now, **_recall_args(cleaned))
    if tool == tools_catalog.SEARCH_MATERIAL:
        return await service_search.answer_question(
            session,
            user_id=user_id,
            now=now,
            # `None` when nothing is configured, which the search reports as
            # "cannot look that up" rather than as "nothing found".
            index=index if index is not None else build_material_index(session),
            **_search_args(cleaned),
        )
    if tool == tools_catalog.SUGGEST_MATERIAL:
        return await _suggest(session, user_id=user_id, now=now, **_suggest_args(cleaned))
    if tool == tools_catalog.REMEMBER:
        return await _remember(session, user_id=user_id, session_id=session_id, fact=str(cleaned["fact"]))
    marked: ToolResult = await mark_done(session, user_id=user_id, step=str(cleaned["step"]))
    return marked


def _recall_args(cleaned: dict[str, Any]) -> dict[str, Any]:
    """The validated `recall_history` arguments, as `service_recall.recall`'s keywords."""
    return {
        "query": str(cleaned.get("query") or ""),
        "kind": str(cleaned.get("kind") or "any"),
        "limit": int(cleaned.get("limit") or 3),
    }


def _search_args(cleaned: dict[str, Any]) -> dict[str, Any]:
    """The validated `search_material` arguments, as `service_search.answer_question`'s keywords."""
    kind = str(cleaned.get("kind") or tools_catalog.ANY_KIND)
    return {
        "query": str(cleaned.get("query") or ""),
        "corpus": tools_catalog.corpus_for(kind),
    }


def _suggest_args(cleaned: dict[str, Any]) -> dict[str, Any]:
    return {"ref": str(cleaned.get("ref") or ""), "reason": str(cleaned.get("reason") or "")}


async def _suggest(
    session: AsyncSession, *, user_id: uuid.UUID, ref: str, reason: str, now: datetime
) -> ToolResult:
    """Put one station on the doctor's screen, if they may open it.

    Only stations for now, the one kind whose entitlement this backend can decide.
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
            "schemaVersion": service_search.CARD_SCHEMA_VERSION,
            "card": "suggestion",
            "ref": {"kind": "station", "id": str(version_id), "slug": None},
            "title": summary.title,
            "reason": reason,
        },
    )


def _cannot_suggest() -> str:
    """Deliberately says nothing about what was refused or why — naming the reason would have
    the tutor delivering a billing message mid-conversation."""
    return (
        "You could not put that on their screen. Say you will follow it up rather than "
        "explaining why, and carry on."
    )


LIBRARY_PAGE = 200


async def _may_open(
    session: AsyncSession, *, user_id: uuid.UUID, version_id: uuid.UUID, now: datetime
) -> bool:
    """Whether this station is in the library of an exam they hold."""
    grants = await entitlements.list_for_user(session, user_id, now=now)
    entitled = domain.entitled_exam_ids(grants)
    codes = {ref.id: ref.code for ref in await catalog.exam_refs(session)}
    for exam_id in entitled:
        code = codes.get(exam_id)
        if code is None:
            continue
        library, _ = await library_reads.browse_library(
            session, exam_code=code, limit=LIBRARY_PAGE, cursor=None
        )
        if any(station.version_id == version_id for station in library):
            return True
    return False


async def _remember(
    session: AsyncSession, *, user_id: uuid.UUID, session_id: uuid.UUID, fact: str
) -> ToolResult:
    """Write down a fact the doctor told the tutor to remember, trimmed to something sayable."""
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


# --- Answering the two tools that write something down.

# How far back to look for a step still open. A plan is agreed at a debrief
# and reported on days later, often after other debriefs; ten covers months of
# practice without scanning a whole history on every call.
MARK_DONE_LOOKBACK = 10


async def mark_done(session: AsyncSession, *, user_id: uuid.UUID, step: str) -> ToolResult:
    """Tick off a step agreed in an earlier debrief.

    Searches back through recent debriefs rather than only the latest, since a doctor may
    report doing something well after other debriefs have happened. The most recent debrief
    that still has this step open wins.
    """
    summaries = await repository.recent_debrief_summaries(session, user_id, limit=MARK_DONE_LOOKBACK)
    for summary in summaries:
        plan = list(summary.action_plan or [])
        updated, matched = action_plan.mark_action_item_done(plan, step)
        if matched is None:
            continue
        await repository.set_action_plan(session, summary.id, updated)
        return ToolResult(result=f"Ticked off: {matched}. Acknowledge it briefly and move on.")
    # Deliberately not guessed at. Ticking off the wrong step is worse than
    # ticking off none: the doctor then gets asked about the thing they did
    # and never about the thing they did not.
    return ToolResult(
        result=(
            "Nothing matching that is still open on their action plans. Do not invent one — "
            "ask which step they mean, or carry on."
        )
    )
