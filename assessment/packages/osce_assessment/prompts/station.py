"""Builds a live-persona system prompt from a stored station document.

One formatter for every station, whoever authored it. A station is a title and
a map of content blocks; a *layout* — the ordered block list from the station
template the station was written against — says what each block is for. The
formatter places blocks by the role the layout gives them, so a new exam is a
new template rather than a new branch in this file.

Without a layout the block ids are matched against the common spellings below,
which is what keeps an untemplated station rendering. Either way an
unrecognised block becomes a titled section the persona holds back until asked:
an author may put anything in their own template, and for a patient persona
volunteering it unprompted is the worse failure.

Blocks the candidate must not hear — the examiner's expected answers, the
marking order — carry the ``examiner`` role and never reach the patient prompt.
They are handed to the marker separately through
:func:`station_examiner_context`. An examiner persona is given them too: they
are the questions it asks, and a viva run without them has nothing to ask.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ._blocks import EXAMINER_NEVER, PATIENT_NEVER, hidden_section, role_lock, speech_rules

__all__ = [
    "KNOWN_ROLES",
    "StationPromptFormatter",
    "create_station_prompt",
    "station_examiner_context",
]

# What a block may be for. A template's author picks one per block; anything
# else is held back and read out only on request. `faculty` is the one role
# that goes nowhere: it is known, so its block is never a leftover read to the
# patient, and neither the live persona nor the marker is given it.
KNOWN_ROLES = (
    "persona",
    "complaint",
    "instructions",
    "history",
    "medications",
    "social",
    "examination",
    "examiner",
    "candidate_brief",
    "hidden",
    "faculty",
)

# Block ids recognised when a station has no template layout: the common
# spellings, kept so a station written before templates still renders.
_ALIASES: dict[str, tuple[str, ...]] = {
    "persona": (
        "patient_description",
        "patientDescription",
        "patient_background",
        "patientBackground",
        "background",
    ),
    "complaint": (
        "presenting_complaint",
        "presentingComplaint",
        "chief_complaint",
        "chiefComplaint",
        "complaint",
    ),
    "instructions": (
        "patient_instructions",
        "patientInstructions",
        "actor_instructions",
        "actorInstructions",
        "instructions",
    ),
    "history": (
        "history",
        "medical_history",
        "medicalHistory",
        "relevant_history",
        "past_medical_history",
        "pastMedicalHistory",
    ),
    "medications": (
        "medications",
        "medication",
        "current_medications",
        "currentMedications",
    ),
    "social": (
        "social_history",
        "socialHistory",
        "social",
    ),
    "examination": (
        "examination",
        "examination_findings",
        "examinationFindings",
        "examination_notes",
    ),
}

# The hidden sections a patient carries, in the order they are read out, with
# the words that introduce each one.
_HELD_BACK: tuple[tuple[str, str, str], ...] = (
    ("history", "your medical history", ""),
    ("medications", "your medications", ""),
    ("social", "your social history", ""),
    (
        "examination",
        "examination findings",
        "Only say this if the doctor examines you or asks for it directly.",
    ),
)

_PERSONAE = {
    "patient": ("the patient", "the doctor", PATIENT_NEVER),
    "examiner": ("the examiner", "the candidate", EXAMINER_NEVER),
}


def _records_text(records: Sequence[Any], fields: Sequence[Mapping[str, Any]]) -> str:
    """A table's rows as `Column: value` lines, a blank line between rows.

    Without the column names a row of observations reads as bare numbers, and
    the persona cannot tell a heart rate from a respiratory rate. Columns are
    written in the template's order, since a stored row's keys come back in
    whatever order the database keeps them; a key the template does not name
    goes last.
    """
    labels = {str(field.get("key")): str(field.get("label") or field.get("key")) for field in fields}
    rows = []
    for record in records:
        if not isinstance(record, Mapping):
            continue
        keys = [key for key in labels if key in record] + [str(key) for key in record if str(key) not in labels]
        lines = [f"{labels.get(key, key)}: {text}" for key in keys if (text := _text_from_value(record.get(key)))]
        if lines:
            rows.append("\n".join(lines))
    return "\n\n".join(rows)


def _text_from_value(val: Any, fields: Sequence[Mapping[str, Any]] | None = None) -> str:
    """A plain string, whether the block holds text, a list, a table or rich text.

    ``fields`` is a table block's column list; with it each row is written
    with its column names.
    """
    if isinstance(val, str):
        return val.strip()
    if fields and isinstance(val, list):
        return _records_text(val, fields)
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
        pieces = [_text_from_value(v) for v in val.values()]
        return "\n".join(p for p in pieces if p)
    return str(val).strip() if val is not None else ""


def _label_for(block_id: str, given: str) -> str:
    return (given or block_id).replace("_", " ").replace("-", " ").strip().lower()


def _by_role(
    content: Mapping[str, Any], layout: Sequence[Mapping[str, Any]] | None
) -> tuple[dict[str, list[str]], list[tuple[str, str]]]:
    """Block text grouped by role, plus the leftovers as (label, text) pairs.

    Leftovers are blocks the layout did not describe, or — with no layout —
    blocks whose id matched none of the known spellings. They keep the order
    the author wrote them in.
    """
    roles: dict[str, list[str]] = {role: [] for role in KNOWN_ROLES}
    claimed: set[str] = set()

    if layout is not None:
        for block in layout:
            block_id = str(block.get("id") or "")
            role = str(block.get("role") or "")
            if not block_id or role not in roles:
                continue
            claimed.add(block_id)
            fields = block.get("fields")
            text = _text_from_value(content.get(block_id), fields if isinstance(fields, list) else None)
            if text:
                roles[role].append(text)
    else:
        for role, ids in _ALIASES.items():
            for block_id in ids:
                claimed.add(block_id)
                text = _text_from_value(content.get(block_id))
                if text and not roles[role]:
                    roles[role].append(text)

    labels = {
        str(block.get("id")): str(block.get("label") or "")
        for block in (layout or ())
        if block.get("id")
    }
    leftovers = [
        (_label_for(key, labels.get(key, "")), text)
        for key, val in content.items()
        if key not in claimed and (text := _text_from_value(val))
    ]
    return roles, leftovers


class StationPromptFormatter:
    """Turn a stored station into the live persona's system prompt."""

    @staticmethod
    def create_prompt(
        station: Mapping[str, Any],
        layout: Sequence[Mapping[str, Any]] | None = None,
        *,
        persona: str = "patient",
    ) -> str:
        """``station`` is ``{"title": str, "content": {block_id: value}}``.

        ``layout`` is the template's ordered block list; ``None`` falls back to
        the common block spellings. ``persona`` casts the model — a viva
        station sets it to ``examiner``.
        """
        title = str(station.get("title") or "OSCE Station")
        content = station.get("content") or {}
        if not isinstance(content, Mapping):
            content = {}
        roles, leftovers = _by_role(content, layout)

        who, counterpart, never = _PERSONAE.get(persona, _PERSONAE["patient"])
        parts = [
            role_lock(persona=who, counterpart=counterpart, never=never),
            speech_rules(),
        ]

        introduction = "\n\n".join(roles["persona"] + roles["complaint"])
        if introduction:
            parts.append(f"<you>\n{introduction}\n</you>")

        parts.append(_how_to_answer(persona))

        for role, label, rule in _HELD_BACK:
            for text in roles[role]:
                parts.append(hidden_section(label, text, rule=rule) if rule else hidden_section(label, text))
        for text in roles["hidden"]:
            parts.append(hidden_section("what you have not been asked yet", text))
        for label, text in leftovers:
            parts.append(hidden_section(label, text))

        instructions = "\n\n".join(roles["instructions"])
        if instructions:
            parts.append(f"<special_instructions>\n{instructions}\n</special_instructions>")

        for text in roles["candidate_brief"]:
            parts.append(f"<what_the_candidate_was_told>\n{text}\n</what_the_candidate_was_told>")

        if persona == "examiner" and roles["examiner"]:
            parts.append(_examiner_material(roles["examiner"]))

        parts.append(_station_title(title, persona))
        return "\n\n".join(part for part in parts if part)

    @staticmethod
    def examiner_context(
        station: Mapping[str, Any], layout: Sequence[Mapping[str, Any]] | None = None
    ) -> str | None:
        """What the marker is told and the candidate is not.

        The expected answers, the expected order, the examiner's own notes:
        blocks the layout gives the ``examiner`` role. Returns ``None`` when
        the station has none, which is the usual case.
        """
        content = station.get("content") or {}
        if not isinstance(content, Mapping):
            return None
        roles, _ = _by_role(content, layout)
        blocks = roles["examiner"]
        if not blocks:
            return None
        body = "\n\n".join(blocks)
        return f"\n\n<examiner_notes>\n{body}\n</examiner_notes>"


def _examiner_material(blocks: Sequence[str]) -> str:
    """The station's questions and expected answers, as the examiner running the viva holds them.

    The same blocks the marker is given. Without them an examiner persona knows
    only what the candidate was told, so it has nothing of the station's own to
    ask. The expected answers are its mark sheet: `EXAMINER_NEVER` already
    forbids revealing them, and this says so where they sit.
    """
    body = "\n\n".join(blocks)
    return (
        "<your_questions_and_expected_answers>\n"
        "Ask the questions the station sets out below. The expected answers are for you alone: "
        "never read them out, hint at them, or say whether an answer matched them.\n\n"
        f"{body}\n"
        "</your_questions_and_expected_answers>"
    )


def _station_title(title: str, persona: str) -> str:
    """The station's name, fenced off when the persona must not say it.

    A station is usually named for its diagnosis. A patient who reads that as a
    heading starts consulting from it; the fence is what stops the name being
    spoken while keeping the answers consistent with it.
    """
    if persona == "patient":
        return (
            "<never_say>\n"
            f"This consultation is simulating: {title}\n"
            "You do not know this. It is written here only so your answers stay consistent with it. "
            "Never say it, never hint at it, and never use the words in it.\n"
            "</never_say>"
        )
    return f"<station>\n{title}\n</station>"


def _how_to_answer(persona: str) -> str:
    if persona == "examiner":
        return (
            "<how_to_answer>\n"
            "Ask what the station sets out, one question at a time, and wait for the answer.\n"
            "Acknowledge without marking. \"Thank you\", \"Let's move on\" and \"Tell me more about that\" all "
            "keep the station running; \"Good\", \"That's right\" and \"Not quite\" all tell the candidate how "
            "they are doing, which is the one thing you must not do. Use the same neutral acknowledgement "
            "whether the answer was right or wrong.\n"
            "If the candidate asks for something the notes below do not cover, say that it is not "
            "available and let them carry on.\n"
            "</how_to_answer>"
        )
    return (
        "<how_to_answer>\n"
        "Wait for the doctor to greet you or ask you something before you speak.\n"
        "Answer what you are actually asked, in everyday words rather than medical ones, and let "
        "the doctor draw your story out of you instead of telling it all at once.\n"
        "Show what you feel where it fits: worry, pain, confusion.\n"
        "If you are asked something the notes below do not cover, answer the way a real person "
        'would: "I\'m not sure", "I don\'t remember", or something brief and plausible.\n'
        "</how_to_answer>"
    )


def create_station_prompt(
    station: Mapping[str, Any],
    layout: Sequence[Mapping[str, Any]] | None = None,
    *,
    persona: str = "patient",
) -> str:
    """Module-level convenience wrapper."""
    return StationPromptFormatter.create_prompt(station, layout, persona=persona)


def station_examiner_context(
    station: Mapping[str, Any], layout: Sequence[Mapping[str, Any]] | None = None
) -> str | None:
    """Module-level convenience wrapper."""
    return StationPromptFormatter.examiner_context(station, layout)
