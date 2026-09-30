"""Client-selected content for the assistant worker: FAQ, greetings, persona, onboarding scenes.

The worker never sees any of this raw. ``assistant_sessions`` resolves a
``ClientProfile`` from the stored session, asks for the matching
``ContentPack``, renders the templates in ``assistant_prompts`` with it, and
ships finished text in the bootstrap.

Packs are layered: ``packs.BASE`` (exam-neutral) + ``packs.EXAM_OVERLAYS[exam]``
+ ``packs.SURFACE_OVERLAYS[surface]``. Entries reference navigation by key
(``{nav.mocks}``) and declare ``requires_nav``, so the client's own catalog
decides the labels and which entries exist.

``employer`` is a known surface this backend does not serve; b2b-api renders
its own pack against the same worker bootstrap contract.
"""

from .models import (
    ADMIN_ROLE,
    SURFACES,
    ClientProfile,
    ContentPack,
    FaqEntry,
    NavItem,
    OnboardingScene,
    Persona,
)
from .overlay import Overlay, OverlayError, apply
from .request import ClientContextError, parse_client_context
from .resolver import UnsupportedSurfaceError, resolve_client_profile, resolve_content_pack

__all__ = [
    "ADMIN_ROLE",
    "SURFACES",
    "ClientContextError",
    "ClientProfile",
    "ContentPack",
    "FaqEntry",
    "NavItem",
    "OnboardingScene",
    "Overlay",
    "OverlayError",
    "Persona",
    "UnsupportedSurfaceError",
    "apply",
    "parse_client_context",
    "resolve_client_profile",
    "resolve_content_pack",
]
