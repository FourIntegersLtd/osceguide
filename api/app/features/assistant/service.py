"""Assistant session use cases, including the worker's side."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ports import VoiceTokens
from app.core.settings import Settings
from app.features.assistant import domain, errors, repository
from app.features.assistant import service_seams as seams
from app.features.assistant.models import AssistantSession
from app.features.assistant.doctor_prompt import consulting_doctor_instructions
from app.features.assistant.schemas import RoomGrant, SessionRead

# Placeholder text until content packs are ported. Rendered here rather than in
# the worker, which holds no templates by design.
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
    row = await require_session(session, session_id)
    if not domain.can_join(status=row.status):
        raise errors.SessionNotJoinable()
    if seams._run_tool is None:
        raise errors.ToolsNotAvailable()
    return await seams._run_tool(
        session,
        tool=tool,
        arguments=arguments,
        user_id=row.user_id,
        session_id=session_id,
        now=now,
    )


async def start_session(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    session_type: str,
    extras: dict[str, Any],
    now: datetime,
) -> SessionRead:
    try:
        worker_type = domain.worker_type_for(session_type)
    except domain.UnknownAssistantType as exc:
        raise errors.UnknownAssistantTypeError(str(exc)) from exc

    # Asked before the placeholder is used, not instead of it: a slice above
    # this one renders the kinds it knows about and answers `None` for the rest.
    rendered = await seams._render(session, worker_type, user_id, now) if seams._render else None
    instructions = str(rendered["instructions"]) if rendered else _INSTRUCTIONS[worker_type]
    greeting = str(rendered["greeting"]) if rendered and rendered.get("greeting") else None
    if worker_type == "consulting-doctor":
        station_instructions = consulting_doctor_instructions(extras)
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

    row = await repository.create_session(
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
    await repository.set_room(session, row.id, room_name=f"assistant_{row.id}")
    refreshed = await repository.by_id(session, row.id)
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

    Without this the assistant existed only on paper: a session could be
    started and a worker could bootstrap it, but no browser could join the
    room, so nothing the assistant does was reachable end to end.

    The metadata is the three strings `livekit_assistant_worker/metadata.py`
    reads. Everything else the worker needs it fetches from the bootstrap
    route, so this does not become a second, drifting copy of the session.
    """
    from app.features.voice import service as voice

    row = await require_session(session, session_id)
    if row.user_id != requester_id:
        raise errors.SessionNotYours()
    if not domain.can_join(status=row.status):
        raise errors.SessionNotJoinable()

    grant = await voice.grant_for_agent_room(
        room=row.room_name or f"assistant_{row.id}",
        session_type=row.session_type,
        identity=str(row.user_id),
        dispatch_metadata={
            "session_id": str(row.id),
            "backend": settings.voice_backend_label,
            "candidate_ref": str(row.user_id),
        },
        tokens=tokens,
        settings=settings,
    )
    return RoomGrant(token=grant.token, server_url=grant.server_url, room=grant.room)


TOOLS_KEY = "tools"


def _tool_extras(rendered: dict[str, Any]) -> dict[str, Any]:
    return {**(rendered.get("extras") or {}), TOOLS_KEY: rendered.get("tools") or []}


async def require_session(session: AsyncSession, session_id: uuid.UUID) -> AssistantSession:
    row = await repository.by_id(session, session_id)
    if row is None:
        raise errors.SessionNotFound()
    return row


def _read(row: AssistantSession) -> SessionRead:
    return SessionRead(
        id=row.id,
        session_type=row.session_type,
        status=row.status,
        room_name=row.room_name,
        created_at=row.created_at,
    )
