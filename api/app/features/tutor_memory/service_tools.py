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

from app.core.ports import GuidelineIndex, MaterialIndex
from app.features.catalog import service as catalog
from app.features.entitlements import service as entitlements
from app.features.identity import service_platform as identity
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
from app.features.tutor_memory.domain import HELP_CORPUS
from app.features.tutor_memory.guidelines import build_guideline_index
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
    guidelines: GuidelineIndex | None = None,
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
            guidelines=guidelines if guidelines is not None else build_guideline_index(),
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
    """Put one station, piece of reading or help page on the doctor's screen, if they may open it.

    The ref decides the kind: a UUID is a station version, a help article's slug
    is help, and any other slug is a media item. Every refusal is the same one.
    """
    try:
        version_id = uuid.UUID(ref)
    except ValueError:
        return await _suggest_by_slug(session, user_id=user_id, slug=ref.strip(), reason=reason, now=now)

    summaries = await stations.summaries_by_version_id(session, None, [version_id])
    summary = summaries.get(version_id)
    if summary is None:
        return ToolResult(result=_cannot_suggest())

    allowed = await _may_open(session, user_id=user_id, version_id=version_id, now=now)
    if not allowed:
        return ToolResult(result=_cannot_suggest())

    # The version is what was practised; the station id is what its library page is addressed by.
    return _suggested(
        kind="station",
        item_id=str(version_id),
        slug=str(summary.station_id),
        title=summary.title,
        reason=reason,
    )


async def _suggest_by_slug(
    session: AsyncSession, *, user_id: uuid.UUID, slug: str, reason: str, now: datetime
) -> ToolResult:
    """A help page this account's exam shows, or a published media item of an exam they hold."""
    from app.features.assistant import service_help  # avoids an import cycle
    from app.features.media import errors as media_errors
    from app.features.media import service as media

    slug = service_search.help_slug(slug)
    user = await identity.user_by_id(session, user_id)
    exam_code = (user.exam_code if user else None) or ""
    article = next((item for item in service_help.list_articles(exam_code) if item.slug == slug), None)
    if article is not None:
        return _suggested(
            kind=HELP_CORPUS, item_id=article.slug, slug=article.slug, title=article.title, reason=reason
        )

    try:
        media_item = await media.read_by_slug(session, slug, viewer_is_admin=False)
    except media_errors.ItemNotFound:
        return ToolResult(result=_cannot_suggest())
    if media_item.exam_code is not None:
        grants = await entitlements.list_for_user(session, user_id, now=now)
        codes = await catalog.exam_codes_by_id(session, list(domain.entitled_exam_ids(grants)))
        if media_item.exam_code not in set(codes.values()):
            return ToolResult(result=_cannot_suggest())
    return _suggested(
        kind=media_item.kind,
        item_id=str(media_item.id),
        slug=media_item.slug,
        title=media_item.title,
        reason=reason,
    )


def _suggested(*, kind: str, item_id: str, slug: str | None, title: str, reason: str) -> ToolResult:
    """The spoken confirmation and the suggestion card, the same for every kind."""
    return ToolResult(
        result=(
            f"Done — {title} is on their screen now. Tell them in one sentence why you "
            "chose it, in your own words."
        ),
        display={
            "type": "assistant_card",
            "schemaVersion": service_search.CARD_SCHEMA_VERSION,
            "card": "suggestion",
            "ref": {"kind": kind, "id": item_id, "slug": slug},
            "title": title,
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
