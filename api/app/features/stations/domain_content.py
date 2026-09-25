"""Which parts of a station document a trainee-only reader may be served.

Pure rules, no session. `attempts/domain_material.py` answers the same
question for a candidate reading through their attempt; this answers it for
the org station list, whose `OrgReader` permission admits every rostered
trainee. Before this existed the list handed each of them the whole document
— the patient's persona and hidden history, the examiner's material, for the
stations they were about to be examined on.

The key tuples are mirrored from `attempts/domain_material.py` rather than
imported: a slice reaches another only through its service, and each slice
owning its copy of a rule is what keeps that true. The *keys* are deliberately
shared — they are one document's vocabulary — so a unit test pins the two
together, the same arrangement the shared `unknown_exam` code has.

A template whose blocks carry custom ids contributes nothing to a trainee
projection unless a block id happens to be one named here; a template can
mark a block `candidate_brief`, and reading one back per station is a lookup
this list route does not make. The conservative default is the point: what is
not named here stays on the server, and the candidate-facing material a
template authored is still readable through the attempt, whose brief read
renders by role.
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
