"""Value types for client-selected assistant content.

A ``ClientProfile`` says who is asking (surface, exam, role) and what the
client currently shows (route, navigation catalog). A ``ContentPack`` is the
resolved content for that profile: persona, greetings, FAQ entries,
onboarding scenes. Framework-free so any backend can reuse the shapes.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

SURFACE_EXAM = "exam"
SURFACE_ADMIN = "admin"
SURFACE_EMPLOYER = "employer"
SURFACES = (SURFACE_EXAM, SURFACE_ADMIN, SURFACE_EMPLOYER)
"""Every surface the contract knows. This backend serves ``exam`` and ``admin``."""

ADMIN_ROLE = "admin"
MAX_ROUTE_CHARS = 200
MAX_NAV_ITEMS = 40
MAX_NAV_FIELD_CHARS = 120


@dataclass(frozen=True)
class NavItem:
    """One entry of the client's navigation as the user currently sees it."""

    key: str
    label: str
    path: str


@dataclass(frozen=True)
class ClientProfile:

    surface: str
    exam: str
    role: str = ""
    route: str = ""
    navigation: tuple[NavItem, ...] = ()

    @property
    def nav_labels(self) -> dict[str, str]:
        return {entry.key: entry.label for entry in self.navigation}


@dataclass(frozen=True)
class Persona:

    assistant_name: str = "Athena"
    product_name: str = "OSCE Guide"


@dataclass(frozen=True)
class FaqEntry:
    """One question the help tool can answer. ``{nav.<key>}`` in text renders to the client's label.

    ``requires_nav`` lists navigation keys the entry only makes sense with;
    the resolver drops the entry when the client's catalog lacks any of them.
    """

    id: str
    section: str
    question: str
    answer: str
    requires_nav: tuple[str, ...] = ()


@dataclass(frozen=True)
class OnboardingScene:

    patient_line: str
    question: str


@dataclass(frozen=True)
class ContentPack:

    persona: Persona = Persona()
    greetings: Mapping[str, str] = field(default_factory=dict)
    """Opening line per worker type; a missing type lets the model open by itself."""
    faq: tuple[FaqEntry, ...] = ()
    no_match_message: str = ""
    onboarding_scenes: tuple[OnboardingScene, ...] = ()
    default_labels: Mapping[str, str] = field(default_factory=dict)
    """Navigation labels used for ``{nav.<key>}`` when the client sent no catalog."""

    def entry_ids(self) -> tuple[str, ...]:
        return tuple(entry.id for entry in self.faq)
