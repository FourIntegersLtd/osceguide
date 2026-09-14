"""The competency frameworks the platform itself publishes.

Content, not structure: the *concept* of a framework lives in
``contracts.framework``, and this module is the set the platform ships. An
organisation's own framework never appears here; when org-authored frameworks
land it will arrive through a provider, exactly as org-owned scenarios do,
and this catalogue becomes one implementation among two.

Every entry carries its result schema as data (see ``schemas/``), which is the
shape the language model is asked to fill. The SCA entry also names the domains
and global skills the platform marks; the other exams carry their schema only
until their competencies are lifted out of it.
"""

from __future__ import annotations

from .contracts.framework import (
    Competency,
    CompetencyDomain,
    CompetencyFramework,
    RAG_SCALE,
)
from .schemas import load_schema

__all__ = [
    "CASC_RCPSYCH_V1",
    "CatalogFrameworkProvider",
    "ORTHO_FRCS_V1",
    "PLAB2_GMC_V1",
    "SCA_RCGP_V1",
    "UnknownFrameworkError",
    "all_frameworks",
    "framework",
    "framework_ids",
]


class UnknownFrameworkError(LookupError):
    """Raised for a framework id that the catalogue does not publish."""


_GLOBAL_SKILLS = CompetencyDomain(id="global_skills", label="Global skills")
_TASKS = CompetencyDomain(id="tasks", label="Tasks")
_RELATING = CompetencyDomain(id="relating_to_others", label="Relating to others")


def _global(id_: str, label: str) -> Competency:
    return Competency(id=id_, label=label, domain_id=_GLOBAL_SKILLS.id)


SCA_RCGP_V1 = CompetencyFramework(
    id="sca-rcgp-v1",
    result_schema=load_schema("sca-rcgp-v1"),
    label="RCGP Simulated Consultation Assessment",
    version="1",
    domains=(_GLOBAL_SKILLS, _TASKS, _RELATING),
    competencies=(
        _global("structures_consultation", "Structures the consultation"),
        _global("avoids_repetition", "Avoids repetition"),
        _global("progresses_through_tasks", "Progresses through the tasks"),
        _global("recognises_ethical_implications", "Recognises ethical implications"),
        _global("finishes_data_gathering", "Finishes data gathering"),
        _global("uses_clear_language", "Uses clear language"),
        _global("remains_responsive_to_patient", "Remains responsive to the patient"),
    ),
    scale=RAG_SCALE,
)

PLAB2_GMC_V1 = CompetencyFramework(
    id="plab2-gmc-v1",
    result_schema=load_schema("plab2-gmc-v1"),
    label="GMC PLAB 2",
    version="1",
    scale=RAG_SCALE,
)

CASC_RCPSYCH_V1 = CompetencyFramework(
    id="casc-rcpsych-v1",
    result_schema=load_schema("casc-rcpsych-v1"),
    label="RCPsych CASC",
    version="1",
    scale=RAG_SCALE,
)

ORTHO_FRCS_V1 = CompetencyFramework(
    id="ortho-frcs-v1",
    result_schema=load_schema("ortho-frcs-v1"),
    label="FRCS Trauma and Orthopaedics",
    version="1",
    scale=RAG_SCALE,
)

_CATALOG: dict[str, CompetencyFramework] = {
    fw.id: fw
    for fw in (SCA_RCGP_V1, PLAB2_GMC_V1, CASC_RCPSYCH_V1, ORTHO_FRCS_V1)
}


def framework(framework_id: str) -> CompetencyFramework:
    try:
        return _CATALOG[framework_id]
    except KeyError:
        raise UnknownFrameworkError(
            f"no published framework {framework_id!r}; "
            f"known: {sorted(_CATALOG)}"
        ) from None


def framework_ids() -> tuple[str, ...]:
    return tuple(_CATALOG)


def all_frameworks() -> tuple[CompetencyFramework, ...]:
    return tuple(_CATALOG.values())


class CatalogFrameworkProvider:
    """The platform catalogue as a ``FrameworkProvider``.

    Consumers with organisation-authored frameworks compose their own provider
    and fall back to this one for the platform's published frameworks.
    """

    def get(self, framework_id: str) -> CompetencyFramework:
        return framework(framework_id)
