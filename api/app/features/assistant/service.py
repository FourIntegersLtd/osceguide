"""Assistant session use cases, including the worker's side."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ports import VoiceTokens
from app.core.settings import Settings
from app.features.assistant import domain, errors, repository, service_content
from app.features.assistant.content import ClientContextError, parse_client_context, parse_topic
from app.features.assistant.doctor_prompt import consulting_doctor_instructions
from app.features.assistant.models import AssistantSession
from app.features.assistant.schemas import RoomGrant, SessionRead
from app.features.tutor_memory import service_session, service_tools

# The last resort, after `tutor_memory` and the content pack have both declined.
# `domain.ensure_dispatchable` refuses a session with no instructions at all,
# and a generic assistant is better than a session that cannot start.
_INSTRUCTIONS = {
    "help": "You are helping someone use OSCE Guide. Answer from the FAQ you have been given.",
    "onboarding": "You are introducing OSCE Guide to someone using it for the first time.",
    "dashboard": "You are talking someone through their progress.",
    "consulting-doctor": "You are a doctor demonstrating a consultation.",
}


async def run_tool(
    session: AsyncSession,
    session_id: uuid.UUID,
    *,
    tool: str,
    arguments: dict[str, Any],
    now: datetime,
) -> dict[str, Any]:
    """Answer one tool call against a live session.

    The session is looked up here rather than by whoever answers, because the
    session's owner and its status are this slice's to know: a tool call must
    not read one person's history on another's session, and a finished session
    has nobody left to answer.
    """
    assistant_session = await require_session(session, session_id)
    if not domain.can_join(status=assistant_session.status):
        raise errors.SessionNotJoinable()
    return await service_tools.tool_hook(
        session,
        tool=tool,
        arguments=arguments,
        user_id=assistant_session.user_id,
        session_id=session_id,
        now=now,
    )


async def _station_context_from_db(
    session: AsyncSession, *, org_id: uuid.UUID | None, station_version_id: uuid.UUID
) -> dict[str, Any] | None:
    """The consulting-doctor station's material, rebuilt from the database.

    SEC-007: the prompt is built from the authored station, scoped to who may
    see it, not from anything the caller sent. A version id the caller cannot
    see (or that does not exist) yields no station, so the session falls back
    to the generic doctor instructions rather than to caller-supplied text.
    """
    from app.features.catalog import service as catalog
    from app.features.stations import service_reads as stations

    material = await stations.version_material(session, org_id, station_version_id)
    if material is None:
        return None
    exam_code = await catalog.exam_code_by_id(session, material.exam_id)
    # The authored document, plus the two fields the prompt names that live on
    # the station row rather than inside its content.
    return {**material.content, "station_name": material.title, "exam_code": exam_code or ""}


async def start_session(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    org_id: uuid.UUID | None,
    session_type: str,
    extras: dict[str, Any],
    station_version_id: uuid.UUID | None,
    now: datetime,
) -> SessionRead:
    """Start a session of this type, rendered from `tutor_memory`, a content pack, or a station.

    Falls back to a generic instruction for the worker type when none of
    those sources has anything to say, so a session always dispatches.
    """
    try:
        worker_type = domain.worker_type_for(session_type)
    except domain.UnknownAssistantType as exc:
        raise errors.UnknownAssistantTypeError(str(exc)) from exc

    # Asked before the placeholder is used, not instead of it: a slice above
    # this one renders the kinds it knows about and answers `None` for the rest.
    rendered = await service_session.render_dashboard_session(
        session,
        session_type=worker_type,
        user_id=user_id,
        now=now,
        client=_client_context(extras),
        topic=_topic(extras),
    )
    instructions = str(rendered["instructions"]) if rendered else ""
    greeting = str(rendered["greeting"]) if rendered and rendered.get("greeting") else None
    # The pack speaks for `help` and `onboarding`; `tutor_memory` owns `dashboard`
    # and answers `None` for everything else, by design.
    from_pack = (
        None
        if rendered
        else await service_content.render(session, worker_type=worker_type, user_id=user_id, extras=extras)
    )
    if from_pack is not None:
        instructions = from_pack.instructions
        greeting = from_pack.greeting
        extras = {**extras, **from_pack.extras}
    instructions = instructions or _INSTRUCTIONS[worker_type]
    if worker_type == "consulting-doctor" and station_version_id is not None:
        # SEC-007: rebuilt from the database, never from `extras`. Without a
        # readable station the demo runs on the generic instructions above.
        station = await _station_context_from_db(
            session, org_id=org_id, station_version_id=station_version_id
        )
        station_instructions = consulting_doctor_instructions({"station": station}) if station else None
        if station_instructions:
            instructions = station_instructions
            greeting = (
                "Hello, I'm Doctor Athena. It's nice to meet you. "
                "Can you confirm your name and date of birth for me?"
            )
    try:
        domain.ensure_dispatchable(instructions=instructions)
    except domain.UnrenderableSession as exc:
        raise errors.SessionNotReady(str(exc)) from exc

    assistant_session = await repository.create_session(
        session,
        user_id=user_id,
        session_type=worker_type,
        instructions=instructions,
        greeting=greeting,
        # The tools the session may call travel with it, so the bootstrap the
        # worker fetches minutes later offers exactly what was rendered for.
        extras={**extras, **(_tool_extras(rendered) if rendered else {})},
        room_name=None,
    )
    # The room is derived from the session id, so a stray room says which
    # session it belongs to.
    await repository.set_room(session, assistant_session.id, room_name=f"assistant_{assistant_session.id}")
    refreshed = await repository.by_id(session, assistant_session.id)
    return _read(refreshed)  # type: ignore[arg-type]


def get_voice_tokens() -> VoiceTokens:
    """The dependency this slice's router wires.

    Delegates rather than re-implements: minting a token is `voice`'s business,
    and a second builder here would be a second place to configure LiveKit.
    Declared in this slice so a test overrides one seam per router, which is
    the convention the other routers already follow.
    """
    from app.features.voice.service import get_voice_tokens as build

    return build()


async def voice_grant(
    session: AsyncSession,
    session_id: uuid.UUID,
    *,
    requester_id: uuid.UUID,
    tokens: VoiceTokens,
    settings: Settings,
) -> RoomGrant:
    """Let this session's owner into its room, with the worker dispatched.

    The metadata is the three strings `livekit_assistant_worker/metadata.py`
    reads. Everything else the worker needs it fetches from the bootstrap
    route, so this does not become a second, drifting copy of the session.
    """
    from app.features.voice import service as voice

    assistant_session = await require_session(session, session_id)
    if assistant_session.user_id != requester_id:
        raise errors.SessionNotYours()
    if not domain.can_join(status=assistant_session.status):
        raise errors.SessionNotJoinable()

    grant = await voice.grant_for_agent_room(
        room=assistant_session.room_name or f"assistant_{assistant_session.id}",
        session_type=assistant_session.session_type,
        identity=str(assistant_session.user_id),
        dispatch_metadata={
            "session_id": str(assistant_session.id),
            "backend": settings.voice_backend_label,
            "candidate_ref": str(assistant_session.user_id),
        },
        tokens=tokens,
        settings=settings,
    )
    return RoomGrant(token=grant.token, server_url=grant.server_url, room=grant.room)


TOOLS_KEY = "tools"


def _tool_extras(rendered: dict[str, Any]) -> dict[str, Any]:
    """`tutor_memory`'s rendered extras, plus the tools it rendered for under `TOOLS_KEY`."""
    return {**(rendered.get("extras") or {}), TOOLS_KEY: rendered.get("tools") or []}


async def require_session(session: AsyncSession, session_id: uuid.UUID) -> AssistantSession:
    """The session with this id, or raise `SessionNotFound`."""
    assistant_session = await repository.by_id(session, session_id)
    if assistant_session is None:
        raise errors.SessionNotFound()
    return assistant_session


def _read(assistant_session: AssistantSession) -> SessionRead:
    """The session's public read shape."""
    return SessionRead(
        id=assistant_session.id,
        session_type=assistant_session.session_type,
        status=assistant_session.status,
        room_name=assistant_session.room_name,
        created_at=assistant_session.created_at,
    )


def _client_context(extras: dict[str, Any]) -> dict[str, Any] | None:
    """The browser's page and menu, validated; a malformed one is dropped, not fatal.

    The tutor is worse without knowing the screen, but a session that refuses
    to start over a bad menu entry is no session at all.
    """
    try:
        return parse_client_context(extras.get("client"))
    except ClientContextError:
        return None


def _topic(extras: dict[str, Any]) -> dict[str, str] | None:
    """What the person opened this conversation to talk about, or `None`.

    A malformed topic is dropped like a malformed client block: the
    conversation still starts, it just opens the usual way.
    """
    try:
        return parse_topic(extras.get("topic"))
    except ClientContextError:
        return None
