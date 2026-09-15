"""
Builds an AI-patient system prompt from an organisation-authored station.

Organisation stations are structured (template-driven), unlike library stations
rendered by ConversationPromptFormatter. This formatter walks the known content
blocks, sweeps any unrecognised block into a titled section so an organisation's
own template shape still renders, and assembles a persona plus consultation
instructions from the same shared blocks as the library prompt.

An unrecognised block is treated as material the patient holds back until
asked. An organisation can put anything in its own template, and for a patient
persona volunteering it unprompted is the worse failure.
"""
from __future__ import annotations

from typing import Any

from ._blocks import PATIENT_NEVER, hidden_section, role_lock, speech_rules


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
                label = key.replace("_", " ").replace("-", " ").lower()
                extra_sections.append(hidden_section(label, text))

        # --- compose prompt ---
        parts = [
            role_lock(persona="the patient", counterpart="the doctor", never=PATIENT_NEVER),
            speech_rules(),
        ]

        who = "\n\n".join(block for block in (patient_desc, complaint) if block)
        if who:
            parts.append(f"<you>\n{who}\n</you>")

        parts.append(
            "<how_to_answer>\n"
            "Wait for the doctor to greet you or ask you something before you speak.\n"
            "Answer what you are actually asked, in everyday words rather than medical ones, and let "
            "the doctor draw your story out of you instead of telling it all at once.\n"
            "Show what you feel where it fits: worry, pain, confusion.\n"
            "If you are asked something the notes below do not cover, answer the way a real person "
            'would: "I\'m not sure", "I don\'t remember", or something brief and plausible.\n'
            "</how_to_answer>"
        )

        parts.append(hidden_section("your medical history", history))
        parts.append(hidden_section("your medications", medications))
        parts.append(hidden_section("your social history", social))
        parts.append(
            hidden_section(
                "examination findings",
                examination,
                rule="Only say this if the doctor examines you or asks for it directly.",
            )
        )
        parts.extend(extra_sections)

        if instructions:
            parts.append(f"<special_instructions>\n{instructions}\n</special_instructions>")

        parts.append(f"<station>\n{title}\n</station>")
        return "\n\n".join(part for part in parts if part)


def create_org_station_prompt(station: dict[str, Any]) -> str:
    """Module-level convenience wrapper."""
    return OrgStationPromptFormatter.create_prompt(station)
