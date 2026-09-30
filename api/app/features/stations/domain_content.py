"""Which parts of a station document a trainee-only reader may be served.

Pure rules, no session, for `GET /orgs/{slug}/stations`'s trainee-scoped list
(`OrgReader` admits every rostered trainee — before this existed the list
handed each of them the whole document, the patient's persona and hidden
history and the examiner's material included, for stations they were about to
be examined on).

A station bound to a template is now projected by its template's `candidate`
audience instead (`stations.service.audience_sections`, called from this
slice's own `service.py`) — a block with a custom id, one that is not
`management_plan` or `doctor_information`, reaches this reader the same way it
reaches the attempt's brief. `candidate_content` below is what a station with
no template, or an unreadable one, falls back to: the same named-key allowlist
every screen used before templates existed. The conservative default is the
point: what is not named here stays on the server.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

# The brief family. `reading_brief` is the key `service_versions.BRIEF_KEY`
# writes and the T5 PATCH route corrects; `candidate_brief` is the older
# spelling authored content and the station generator still use.
BRIEF_KEYS = ("reading_brief", "candidate_brief")

# Mirrored from attempts/domain_material.SCENARIO_KEYS: candidate-facing
# material flat on the document rather than in a block (Ortho's shape).
SCENARIO_KEYS = (
    "station_type",
    "clinical_scenario_title",
    "clinical_scenario",
    "radiograph_image_url",
    "additional_image_urls",
    "background_overview",
    "patient_list_for_candidate",
    "duration_minutes",
)

# Mirrored from attempts/domain_material.PATIENT_BLOCKS: where the patient's
# material lives in the nested shapes.
PATIENT_BLOCKS = ("patient_information", "patient_info")

# Of a patient block, only the identity lines the candidate's own brief read
# discloses (`PatientIdentityRead`) — never the persona, the opening line or
# the hidden history, which are how the patient is played.
PATIENT_IDENTITY_KEYS = ("patient_biodata", "gender")

# Everything a trainee-only reader keeps, flat on the document. Named rather
# than derived: a station gains keys as exams are added, and a rule that said
# "everything except the patient block" would hand over each new one by
# default. `management_plan` and the teaching keys are absent on purpose —
# they are the review, readable once a consultation is over, not before.
CANDIDATE_FACING_KEYS = frozenset(BRIEF_KEYS + SCENARIO_KEYS + ("doctor_information", "patient_gender"))


def candidate_content(content: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """The station document reduced to what a candidate may read of it.

    `None` in, `None` out: a station with no version has no document, and an
    empty dict would read as one that was written and blanked.
    """
    if content is None:
        return None
    projected = {key: value for key, value in content.items() if key in CANDIDATE_FACING_KEYS}
    for key in PATIENT_BLOCKS:
        block = content.get(key)
        if not isinstance(block, Mapping):
            continue
        identity = {name: block[name] for name in PATIENT_IDENTITY_KEYS if name in block}
        # Only when something survives: an empty patient block would render
        # as a section with nothing in it.
        if identity:
            projected[key] = identity
    return projected


def content_for_template(content: Mapping[str, Any] | None, sections: list[Any]) -> dict[str, Any]:
    """The document as a template's blocks read it: each block's value under its own id.

    The engine reads a bound station flat, `content[block_id]`. Stations
    imported from b2c keep their sections nested (`patient_information`,
    `doctor_information`, `management_plan`), and the platform templates for
    those exams name their sections the same way, so a block is looked up in
    the section dict of the same id — by its own id, then without the
    section's prefix (`doctor_patient_biodata` is `doctor_information`'s
    `patient_biodata`). A section dict that was read from is replaced by the
    blocks lifted out of it, so its material reaches the patient only under
    its block's role and never whole. Everything else stays as stored, which
    is all a station authored flat against its template ever holds.
    """
    source = dict(content or {})
    lifted: dict[str, Any] = {}
    consumed: set[str] = set()
    for section in sections:
        if not isinstance(section, Mapping):
            continue
        section_id = str(section.get("id") or "")
        nested = source.get(section_id)
        if not section_id or not isinstance(nested, Mapping):
            continue
        consumed.add(section_id)
        prefix = section_id.split("_", 1)[0] + "_"
        for block in section.get("blocks") or []:
            block_id = str(block.get("id") or "") if isinstance(block, Mapping) else ""
            if block_id in nested:
                lifted[block_id] = nested[block_id]
            elif block_id and block_id.removeprefix(prefix) in nested:
                lifted[block_id] = nested[block_id.removeprefix(prefix)]
    kept = {key: value for key, value in source.items() if key not in consumed}
    return kept | lifted
