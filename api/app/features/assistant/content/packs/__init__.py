"""The content packs: one exam-neutral base plus overlays keyed by exam and by surface.

Keep wording aligned with the live app's tab and button names. Navigation
labels are never written here: entries use ``{nav.<key>}`` and the client's
catalog supplies the label. ``DEFAULT_LABELS`` is only the fallback for
callers that send no catalog.
"""

from __future__ import annotations

from ..models import SURFACE_ADMIN, ContentPack, Persona
from ..overlay import Overlay
from . import (
    admin,
    base_account,
    base_navigation,
    base_practice,
    base_progress,
    base_station,
    exam_other,
    exam_sca,
)

DEFAULT_LABELS = {
    "admin": "Admin",
    "dashboard": "Dashboard",
    "mocks": "AI Practice",
    "summary": "A to Z",
    "messages": "Contact & Feedback",
    "slides": "Slides",
    "community": "Community",
    "marketplace": "Marketplace",
    "settings": "Settings",
    "examinations": "Exam tutor",
    "achievements": "Achievements",
}

GREETINGS = {
    "dashboard": (
        "Hello doctor. Based on your recent consultations, we've analyzed specific areas "
        "where we think we can focus on enhancing your clinical performance. Would you "
        "like to explore these opportunities for improvement together?"
    ),
    "athena-doctor": "Hello, I'm Doctor Athena... It's nice to meet you. Can you confirm your name and date of birth for me ?",
    # Help is text "Help", not a persona: Athena is the voice of the clinical surfaces.
    "help": "Hi, this is Help. Ask me anything about finding your way around the application.",
}

NO_MATCH_MESSAGE = "Tell the user you cannot answer from the FAQ list and direct them to {nav.messages} in the left navigation bar."

BASE = ContentPack(
    persona=Persona(),
    greetings=GREETINGS,
    faq=(
        base_navigation.ENTRIES
        + base_practice.ENTRIES
        + base_station.ENTRIES
        + base_progress.ENTRIES
        + base_account.ENTRIES
    ),
    no_match_message=NO_MATCH_MESSAGE,
    onboarding_scenes=exam_sca.ONBOARDING_SCENES,
    default_labels=DEFAULT_LABELS,
)

EXAM_OVERLAYS: dict[str, Overlay] = {
    "sca": exam_sca.OVERLAY,
    "plab": exam_other.PLAB_OVERLAY,
    "casc": exam_other.CASC_OVERLAY,
    "ortho": exam_other.ORTHO_OVERLAY,
}

SURFACE_OVERLAYS: dict[str, Overlay] = {
    SURFACE_ADMIN: admin.OVERLAY,
}

__all__ = ["BASE", "DEFAULT_LABELS", "EXAM_OVERLAYS", "GREETINGS", "NO_MATCH_MESSAGE", "SURFACE_OVERLAYS"]
