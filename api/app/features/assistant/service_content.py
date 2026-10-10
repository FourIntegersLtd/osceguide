"""Rendering a session's instructions from the content pack.

`service.start_session` asks `tutor_memory` first — it owns the `dashboard`
kind and renders it from somebody's own history — then here, and only then
the placeholder: `domain.ensure_dispatchable` refuses a session with no
instructions at all, and an undispatchable session is worse than a generic
one.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.assistant.content import (
    ADMIN_ROLE,
    ClientProfile,
    ContentPack,
    OnboardingScene,
    UnsupportedSurfaceError,
    resolve_client_profile,
    resolve_content_pack,
)
from app.features.assistant.content.prompts.help import HelpInstructions
from app.features.assistant.content.prompts.onboarding import OnboardingInstructions
from app.features.identity import service_platform as identity

SCENES_KEY = "onboarding_scenes"


@dataclass(frozen=True)
class Rendered:
    """A worker type's rendered instructions, greeting, and any extras to freeze onto the session."""

    instructions: str
    greeting: str | None
    extras: dict[str, Any]


async def _who(
    session: AsyncSession, *, user_id: uuid.UUID, extras: dict[str, Any]
) -> tuple[ClientProfile, str]:
    """Who is asking, and what their screen currently shows.

    The exam is the account's own, not the client's claim: a consumer has one
    exam and the backend answers it once, so a browser cannot ask for another
    exam's content by sending a different string.
    """
    user = await identity.user_by_id(session, user_id)
    profile = resolve_client_profile(
        {
            "client": extras.get("client"),
            "exam_code": (user.exam_code if user else None) or "",
            "role": ADMIN_ROLE if user and user.is_platform_admin else "user",
        }
    )
    return profile, (user.name if user else "")


async def pack_for(session: AsyncSession, *, user_id: uuid.UUID, extras: dict[str, Any]) -> ContentPack:
    """The pack this person's screen should be answered from.

    Public because the onboarding-scenes route needs the same pack the
    instructions were rendered from, and resolving it twice from two places is
    how the scenes and the script drift apart.
    """
    profile, _ = await _who(session, user_id=user_id, extras=extras)
    return resolve_content_pack(profile)


async def render(
    session: AsyncSession, *, worker_type: str, user_id: uuid.UUID, extras: dict[str, Any]
) -> Rendered | None:
    """The instructions for a kind this pack speaks for, or `None`.

    `None` rather than a raise, so an unknown kind falls through to whatever
    the caller does next instead of failing a session somebody is waiting on.
    """
    if worker_type not in {"help", "onboarding"}:
        return None
    try:
        profile, user_name = await _who(session, user_id=user_id, extras=extras)
    except UnsupportedSurfaceError:
        # `employer` is B2B exam mode on this platform, not a product with its
        # own pack, so a session claiming it is a caller bug rather than
        # content nobody has written yet. Left to the fallback, not raised: a
        # bad `surface` should not cost somebody their session.
        return None
    pack = resolve_content_pack(profile)

    if worker_type == "help":
        return Rendered(
            instructions=HelpInstructions(pack, profile).get_help_instructions(),
            greeting=pack.greetings.get("help"),
            extras={},
        )

    scenes = pack.onboarding_scenes
    phase, current = _onboarding_start(extras, scenes)
    instructions = OnboardingInstructions(
        question=current.question if current else "",
        patient_line=current.patient_line if current else "",
        phase=phase,
        user_name=user_name,
        persona=pack.persona,
    ).get_onboarding_instructions()
    return Rendered(
        instructions=instructions,
        greeting=pack.greetings.get("onboarding"),
        # Frozen onto the session for the same reason the tools are: what the
        # worker is offered minutes later must be what these instructions were
        # written against, not whatever the pack says by then.
        extras={SCENES_KEY: [scene_payload(scene) for scene in scenes]},
    )


def _onboarding_start(
    extras: dict[str, Any], scenes: tuple[OnboardingScene, ...]
) -> tuple[str, OnboardingScene | None]:
    """Where the walkthrough is when voice is turned on: the introduction, or a demo scene.

    The browser names a scene by its position in this pack, never by its
    text, so a start request cannot hand the model a script of its own.
    Anything that is not a real demo scene opens on the introduction.
    """
    start = extras.get("onboarding")
    if isinstance(start, dict) and start.get("phase") == "demo":
        index = start.get("scene")
        if isinstance(index, int) and not isinstance(index, bool) and 0 <= index < len(scenes):
            return "demo", scenes[index]
    return "intro", scenes[0] if scenes else None


def scene_payload(scene: Any) -> dict[str, str]:
    """The worker's and the browser's spelling of a scene."""
    return {"patientLine": scene.patient_line, "question": scene.question}
