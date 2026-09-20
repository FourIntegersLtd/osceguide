"""Platform stricter field hints that override B2C profile defaults where needed."""

from __future__ import annotations

PLATFORM_BLOCK_HINT_OVERRIDES: dict[str, str] = {
    "recent_notes": (
        "Past GP or clinic visits only — what is already on the record before today. "
        "Do NOT describe today's presentation, working diagnosis, or examination findings "
        "(no RLQ pain, no 'suspected appendicitis', no acute symptom lists). "
        "Often use a single line such as 'No recent GP visits' or a benign unrelated entry "
        "(e.g. 'Seen 3 months ago for URTI', 'Repeat prescription review 6 weeks ago'). "
        "0–3 items; empty list is acceptable when nothing relevant is documented."
    ),
    "opening_sentence": (
        "A SHORT first-person spoken line the simulated patient says to open the consultation. "
        "This is read aloud by the AI patient partner — write it as the patient speaking, not the examiner. "
        "Do NOT start with 'Hi doctor' or 'Hello' (the session speaks its own greeting first). "
        "Do NOT write a full history here — put detail in expanded_history instead. "
        "Use 1–3 sentences max; natural speech with optional '...' pauses is fine. "
        "Lead with the presenting problem and an emotional or psychosocial hook when relevant."
    ),
    "doctor_patient_biodata": (
        "Short identifiers for the candidate notes (name, age). Not the full AI patient line. "
        "Example: 'Aisha Khan, 24'."
    ),
}
