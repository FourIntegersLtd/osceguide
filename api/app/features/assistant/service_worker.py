"""The worker side of the assistant contract.

Split from `service.py` so the browser-facing use cases and the machine-facing
ones can be read on their own; they change for different reasons, and together
they were past the file cap.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.assistant import domain, errors, repository
from app.features.assistant import service_seams as seams
from app.features.assistant.content.prompts.onboarding import OnboardingInstructions
from app.features.assistant.schemas import WorkerSessionPayload
from app.features.assistant.service import TOOLS_KEY, require_session
from app.features.assistant.service_content import SCENES_KEY


async def bootstrap(session: AsyncSession, session_id: uuid.UUID) -> WorkerSessionPayload:
    """What the assistant worker fetches.

    Mirrors `livekit_assistant_worker.bootstrap.AssistantSession`: every text
    arrives rendered, and `extras` carries the two facts the worker decides for
    itself.
    """
    row = await require_session(session, session_id)
    if not domain.can_join(status=row.status):
        raise errors.SessionNotJoinable()
    try:
        domain.ensure_dispatchable(instructions=row.instructions)
    except domain.UnrenderableSession as exc:
        raise errors.SessionNotReady(str(exc)) from exc

    stored = dict(row.extras or {})
    tools = stored.pop(TOOLS_KEY, [])
    return WorkerSessionPayload(
        session={
            "session_id": str(row.id),
            "worker_type": row.session_type,
            "candidate_ref": str(row.user_id),
            "instructions": row.instructions,
            "greeting": row.greeting,
            "extras": stored,
            # `livekit_assistant_worker.bootstrap.AssistantSession.tools`. An
            # empty list is the whole of the old behaviour, which is why the
            # worker change could ship before any backend defined a tool.
            "tools": tools,
        }
    )


async def scene_instructions(
    session: AsyncSession,
    session_id: uuid.UUID,
    *,
    phase: str | None,
    question: str | None = None,
    patient_line: str | None = None,
) -> str:
    """Instructions for the next scene of an onboarding demo.

    The scene comes from what was frozen onto the session when it started, for
    the same reason the tools are frozen there: the walkthrough the worker
    performs minutes later has to be the one its opening script promised. What
    the worker sends is preferred only when it names a scene this session was
    actually given — otherwise a request could hand the model any script it
    liked.
    """
    row = await require_session(session, session_id)
    scenes = [s for s in (row.extras or {}).get(SCENES_KEY, []) if isinstance(s, dict)]
    scene = _matching_scene(scenes, question=question, patient_line=patient_line)
    if scene is None and phase != "intro":
        scene = scenes[0] if scenes else None
    if scene is None and phase != "intro":
        # Nothing to demonstrate: the pack resolved to no scenes, so the
        # session keeps the instructions it opened with rather than being
        # handed an empty scenario to improvise around.
        return row.instructions
    return OnboardingInstructions(
        question=str(scene.get("question", "")) if scene else "",
        patient_line=str(scene.get("patientLine", "")) if scene else "",
        phase=phase or "demo",
        user_name=await _user_name(session, row.user_id),
    ).get_onboarding_instructions()


def _matching_scene(
    scenes: list[dict[str, Any]], *, question: str | None, patient_line: str | None
) -> dict[str, Any] | None:
    wanted = (question or "").strip()
    line = (patient_line or "").strip()
    for scene in scenes:
        if wanted and str(scene.get("question", "")).strip() == wanted:
            return scene
        if line and str(scene.get("patientLine", "")).strip() == line:
            return scene
    return None


async def _user_name(session: AsyncSession, user_id: uuid.UUID) -> str:
    from app.features.identity import service_platform as identity

    user = await identity.user_by_id(session, user_id)
    return user.name if user else ""


async def accept_transcript(
    session: AsyncSession, session_id: uuid.UUID, *, transcript: dict[str, Any], now: datetime
) -> None:
    """Store the turns, or not, according to what this kind of session is for.

    Three fates rather than two, once `tutor_memory` is bound: a help session
    is retained, a dashboard session is retained *and* queued for summarising
    so the job can replace it, and the rest are discarded unread. Unbound, this
    is the old "help sessions only" rule exactly.
    """
    row = await require_session(session, session_id)
    # Whether to keep this kind of conversation is decided above this slice
    # once `tutor_memory` is bound: a dashboard session is summarised and then
    # deleted, which is neither "keep" nor "discard". Unbound, this is the old
    # rule exactly.
    keep = (
        await seams._on_transcript(session, session_id, row.session_type)
        if seams._on_transcript
        else domain.keeps_transcript(row.session_type)
    )
    if not keep:
        return

    seen = await repository.seen_message_ids(session, session_id)
    for message in transcript.get("messages") or []:
        message_id = str(message.get("message_id") or "")
        if not message_id or message_id in seen:
            continue
        seen.add(message_id)
        await repository.add_message(
            session,
            session_id,
            message_id=message_id,
            seq=int(message.get("seq") or 0),
            role=str(message.get("role") or "user"),
            message=str(message.get("message") or ""),
            spoken_at=now,
        )


async def complete_session(
    session: AsyncSession,
    session_id: uuid.UUID,
    *,
    end_reason: str | None,
    usage: dict[str, Any],
    now: datetime,
) -> None:
    await require_session(session, session_id)
    await repository.complete(session, session_id, at=now, end_reason=end_reason, usage=usage or None)
