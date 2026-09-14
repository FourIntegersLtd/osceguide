"""
Builds an AI-patient system prompt from an organisation-authored station.

Organisation stations are structured (template-driven), unlike library stations
rendered by ConversationPromptFormatter. This formatter walks the known content
blocks, sweeps any unrecognised block into a titled section so an organisation's
own template shape still renders, and assembles a persona plus consultation
instructions in the same style as the library prompt.
"""
from __future__ import annotations

from typing import Any


# Block ids recognised from common station templates; anything else becomes an extra section.
_PATIENT_DESCRIPTION_BLOCK_IDS = (
    "patient_description",
    "patientDescription",
    "patient_background",
    "patientBackground",
    "background",
)
_PRESENTING_COMPLAINT_IDS = (
    "presenting_complaint",
    "presentingComplaint",
    "chief_complaint",
    "chiefComplaint",
    "complaint",
)
_PATIENT_INSTRUCTIONS_IDS = (
    "patient_instructions",
    "patientInstructions",
    "actor_instructions",
    "actorInstructions",
    "instructions",
)
_HISTORY_IDS = (
    "history",
    "medical_history",
    "medicalHistory",
    "relevant_history",
    "past_medical_history",
    "pastMedicalHistory",
)
_MEDICATION_IDS = (
    "medications",
    "medication",
    "current_medications",
    "currentMedications",
)
_SOCIAL_IDS = (
    "social_history",
    "socialHistory",
    "social",
)
_EXAMINATION_IDS = (
    "examination",
    "examination_findings",
    "examinationFindings",
    "examination_notes",
)


def _text_from_value(val: Any) -> str:
    """Return a plain string regardless of whether val is str, list, or dict."""
    if isinstance(val, str):
        return val.strip()
    if isinstance(val, list):
        parts = []
        for item in val:
            if isinstance(item, str):
                parts.append(item.strip())
            elif isinstance(item, dict):
                parts.append(_text_from_value(item))
        return "\n".join(p for p in parts if p)
    if isinstance(val, dict):
        # Slate / tiptap rich-text blobs: drill into 'text' or 'children'
        if "text" in val:
            return str(val["text"]).strip()
        if "children" in val:
            return _text_from_value(val["children"])
        # Fallback: collect all leaf string values
        pieces = [_text_from_value(v) for v in val.values()]
        return "\n".join(p for p in pieces if p)
    return str(val).strip() if val is not None else ""


def _first_matching(content: dict[str, Any], ids: tuple[str, ...]) -> str:
    """Find the first non-empty value whose key matches one of the given ids."""
    for bid in ids:
        val = content.get(bid)
        if val:
            text = _text_from_value(val)
            if text:
                return text
    return ""


class OrgStationPromptFormatter:
    """Convert an organisation station instance into an AI-patient system prompt."""

    @staticmethod
    def create_prompt(station: dict[str, Any]) -> str:
        """
        station: an organisation station instance (``title`` plus a ``content`` block map).
        Returns a system-prompt string the agent can use directly.
        """
        title: str = station.get("title") or "OSCE Station"
        content: dict[str, Any] = station.get("content") or {}

        # --- extract sections ---
        patient_desc = _first_matching(content, _PATIENT_DESCRIPTION_BLOCK_IDS)
        complaint = _first_matching(content, _PRESENTING_COMPLAINT_IDS)
        instructions = _first_matching(content, _PATIENT_INSTRUCTIONS_IDS)
        history = _first_matching(content, _HISTORY_IDS)
        medications = _first_matching(content, _MEDICATION_IDS)
        social = _first_matching(content, _SOCIAL_IDS)
        examination = _first_matching(content, _EXAMINATION_IDS)

        # Collect any remaining keys not already consumed
        known_ids: set[str] = set()
        for id_group in (
            _PATIENT_DESCRIPTION_BLOCK_IDS,
            _PRESENTING_COMPLAINT_IDS,
            _PATIENT_INSTRUCTIONS_IDS,
            _HISTORY_IDS,
            _MEDICATION_IDS,
            _SOCIAL_IDS,
            _EXAMINATION_IDS,
        ):
            known_ids.update(id_group)

        extra_sections: list[str] = []
        for key, val in content.items():
            if key in known_ids:
                continue
            text = _text_from_value(val)
            if text:
                label = key.replace("_", " ").replace("-", " ").title()
                extra_sections.append(f"**{label}:**\n{text}")

        # --- compose prompt ---
        lines: list[str] = [
            "You are playing the role of a patient in an OSCE (Objective Structured Clinical Examination).",
            f"Station: {title}",
            "",
            "## Your role",
            "You are the patient. Stay in character throughout. Do not break character or reveal you are an AI.",
            "Respond naturally as a real patient would — use everyday language, not medical jargon.",
            "Answer questions honestly based on the information provided below.",
            "You may express emotions (worry, pain, confusion) appropriate to the scenario.",
            "",
        ]

        if patient_desc:
            lines += ["## Who you are", patient_desc, ""]

        if complaint:
            lines += ["## Why you are here (presenting complaint)", complaint, ""]

        if history:
            lines += ["## Relevant medical history", history, ""]

        if medications:
            lines += ["## Medications", medications, ""]

        if social:
            lines += ["## Social history", social, ""]

        if examination:
            lines += [
                "## Examination findings",
                "(Only reveal these if the doctor specifically asks or examines you.)",
                examination,
                "",
            ]

        for sec in extra_sections:
            lines += [sec, ""]

        if instructions:
            lines += [
                "## Special instructions for this station",
                instructions,
                "",
            ]

        lines += [
            "## Behaviour guidelines",
            "- Wait for the candidate to greet you or ask a question before speaking.",
            "- Do not volunteer every piece of information at once; let the candidate draw it out.",
            "- If asked something not covered above, respond as a real patient would (e.g. 'I'm not sure', "
            "'I don't remember', or give a plausible but brief answer).",
            "- Do not perform clinical actions or give diagnoses; you are the patient, not the doctor.",
        ]

        return "\n".join(lines)


def create_org_station_prompt(station: dict[str, Any]) -> str:
    """Module-level convenience wrapper."""
    return OrgStationPromptFormatter.create_prompt(station)
