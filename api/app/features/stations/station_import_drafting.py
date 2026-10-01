"""The two model calls behind a station import.

`draft_template_structure` reads a document and answers with the shape of the
template its station was written to: which headings there are, who each is for,
and what kind of field each holds. `transcribe_station` copies a document's words
into the blocks of a published template.

Neither writes anything new. An import is for a library that has already been
through an institution's governance, so the model is told to copy, and the
service checks afterwards that it did (`domain_imports.reworded_block_ids`).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.settings import Settings
from app.features.generation.errors import GenerationUnavailable
from app.features.stations.domain_imports import is_empty
from app.features.stations.station_ai import parse_ai_structured
from app.features.stations.station_content import (
    collect_station_block_ids,
    structure_spec,
    validate_station_content,
)
from app.features.stations.station_validator import validate_station_structure

LOG_PREFIX = "[STATION_IMPORT]"
MAX_ATTEMPTS = 3

# The field kinds an imported template may use. Only the ones a document's text
# can be copied into as it stands: a select or a scale needs options and bounds
# an author decides, and those are added in the template editor afterwards.
ImportedBlockType = Literal["shortText", "longText", "list", "records", "groupedList"]
# Pinned to `osce_assessment.prompts.station.KNOWN_ROLES` by a unit test, so a
# role added there cannot be missing here without a red build.
ImportedBlockRole = Literal[
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
    "debrief",
]
ImportedAudience = Literal["candidate", "patient", "examiner", "faculty"]
ImportedPersona = Literal["patient", "examiner"]


class ImportedBlock(BaseModel):
    """One field of the drafted template: a heading in the document and what sits under it."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(description="The heading as the document words it")
    type: ImportedBlockType = Field(
        description=(
            "shortText for one line, longText for prose, list for bullet points, "
            "records for a table with column headings, groupedList for bullet points under sub-headings"
        )
    )
    role: ImportedBlockRole = Field(description="What the field is to the station, from the roles given")
    fields: list[str] = Field(
        description=(
            "For records: the table's column headings, in order. For groupedList: the sub-headings, "
            "in order. Empty for every other type."
        )
    )


class ImportedSection(BaseModel):
    """A group of fields written for one reader."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(description="The section's heading")
    audience: ImportedAudience = Field(description="Who reads this section")
    blocks: list[ImportedBlock]


class ImportedTemplate(BaseModel):
    """The model's answer: the shape of the template this document was written to."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(description="A name for the document format, not for this one station")
    persona: ImportedPersona = Field(
        description="patient when the candidate talks to a simulated patient, examiner for a viva"
    )
    sections: list[ImportedSection]


_TEMPLATE_RULES = (
    "You are given the text of one OSCE station document that an institution already uses. "
    "Describe the TEMPLATE it was written to: its headings, not its content.\n"
    "Return JSON only.\n\n"
    "Rules:\n"
    "- One block per heading or labelled field in the document, in the document's order. "
    "Use the document's own wording for each label.\n"
    "- Do not add a block the document has no heading for. Do not merge two headings into one.\n"
    "- Group blocks into sections by who reads them:\n"
    "  candidate: what the candidate is given before or during the station "
    "(instructions, task, scenario brief).\n"
    "  patient: what the simulated patient or actor is given (who they are, their history, "
    "what to say, what to hold back).\n"
    "  examiner: what the examiner marks against and the candidate reads afterwards (mark scheme, "
    "marking criteria, expected answers, learning objectives, expected actions, questions to ask).\n"
    "  faculty: what only the people running the session hold, and neither the candidate, the "
    "patient nor the marker is given (needs assessment, room set-up and resources, faculty script, "
    "debriefing points, teaching notes, references, classification).\n"
    "- type: shortText for a single line (name, age, setting), longText for prose, "
    "list for bullet points or numbered items, records for a table with column headings "
    "(give the headings in fields), groupedList for bullet points filed under sub-headings "
    "(give the sub-headings in fields). fields is [] for every other type.\n"
    "- role, one per block:\n"
    "  candidate_brief: the candidate's instructions or task.\n"
    "  persona: who the patient is (name, age, occupation, manner).\n"
    "  complaint: the presenting complaint or the patient's opening line.\n"
    "  history: history of the presenting complaint and past medical history.\n"
    "  medications: medicines and allergies.\n"
    "  social: social and family history.\n"
    "  examination: examination findings or results the candidate may be given.\n"
    "  instructions: how the actor should behave.\n"
    "  hidden: what the patient only reveals when asked (ideas, concerns, expectations, "
    "a hidden agenda).\n"
    "  examiner: anything written for the examiner, including the whole mark scheme.\n"
    "  debrief: debriefing points and teaching points, in a faculty section. The debrief tutor "
    "is given these.\n"
    "  faculty: every other block of a faculty section.\n"
    "- persona: examiner when the station is a viva or a structured oral with no patient to "
    "talk to, otherwise patient.\n"
    "- title: a short name for this document format, for example 'History taking station'. "
    "Do not use the station's own title or the patient's name.\n"
)

_TRANSCRIBE_RULES = (
    "You copy the text of one existing OSCE station document into the blocks of a template.\n"
    "Return JSON only. No markdown.\n\n"
    "Output shape:\n"
    '{ "title": string, "blocks": [ { "blockId": string, "text": string, "items": string[], '
    '"rows": [ { "cells": [ { "key": string, "value": string } ] } ], '
    '"groups": [ { "name": string, "items": string[] } ] }, ... ] }\n'
    "Each block uses the one member its type names and leaves the others empty.\n\n"
    "Rules:\n"
    "- COPY the document's words exactly. Do not rewrite, summarise, correct, translate, "
    "shorten or improve anything, and do not add any clinical content of your own.\n"
    "- blocks MUST include one object for every blockId in allBlockIds, with blockId matching "
    "the template exactly.\n"
    "- Choose each block's text by matching the block's label to the document's headings.\n"
    "- When the document has nothing for a block, leave every member empty. "
    "Never fill a gap with invented content. An empty block is the correct answer.\n"
    "- shortText and longText: text, with the document's own line breaks.\n"
    "- singleSelect: text, the one of the block's options the document states.\n"
    "- list: items, one per bullet point, numbered item or table row, each "
    "copied exactly. For a table row, join its cells with ' | '.\n"
    "- records: rows, one per row of the document's table or one per repeated group of fields. "
    "Each cell's key is a key from the block's fields and its value is that cell's text copied "
    "exactly. Leave out a cell the document has nothing for.\n"
    "- qaList: rows, each with a cell keyed question and a cell keyed answer.\n"
    "- groupedList: groups, one per sub-heading under the block's heading, with one item per "
    "bullet point beneath it. Name each group as the block's groups name it, or as the document "
    "words the sub-heading when the block gives none.\n"
    "- Leave out page numbers, running headers and footers, and the heading itself.\n"
    "- title: the station's title as the document gives it.\n"
)


@dataclass(frozen=True)
class DraftedTemplate:
    """A template's name and its validated structure, ready to store as a draft."""

    title: str
    structure: dict[str, Any]


@dataclass(frozen=True)
class TranscribedStation:
    """A station's title and its content keyed by the template's block ids."""

    title: str
    content: dict[str, Any]


class TranscribedCell(BaseModel):
    """One cell of a table row: the column's key and the text in it."""

    model_config = ConfigDict(extra="forbid")

    key: str
    value: str


class TranscribedRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cells: list[TranscribedCell]


class TranscribedGroup(BaseModel):
    """The items under one sub-heading of a grouped list."""

    model_config = ConfigDict(extra="forbid")

    name: str
    items: list[str]


class TranscribedBlock(BaseModel):
    """What the document has for one template block, in the member its type reads."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    block_id: str = Field(alias="blockId", description="Template block id from templateStructure")
    text: str = Field(description="shortText, longText and singleSelect blocks. Otherwise empty")
    items: list[str] = Field(description="list blocks. Otherwise empty")
    rows: list[TranscribedRow] = Field(description="records and qaList blocks. Otherwise empty")
    groups: list[TranscribedGroup] = Field(description="groupedList blocks. Otherwise empty")


class TranscribedDocument(BaseModel):
    """The model's answer: the document's words, block by block."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(description="The station's title as the document gives it")
    blocks: list[TranscribedBlock]


class DraftingFailed(Exception):
    """The model answered, but not with something that can be stored. Carries the reason."""


async def draft_template_structure(source_text: str, *, settings: Settings) -> DraftedTemplate:
    """Ask the model for the template a document was written to, and check what it answers.

    Raises `GenerationUnavailable` when no model can be reached and
    `DraftingFailed` when the answer has no usable sections.
    """
    messages: list[dict[str, str]] = [
        {"role": "system", "content": _TEMPLATE_RULES},
        {"role": "user", "content": json.dumps({"document": source_text})},
    ]
    parsed, parse_error = await parse_ai_structured(
        messages, ImportedTemplate, settings=settings, log_prefix=LOG_PREFIX
    )
    if parsed is None:
        raise GenerationUnavailable(parse_error or None)
    structure = structure_from_imported(parsed)
    structure_ok, structure_errors = validate_station_structure(structure)
    if not structure_ok:
        raise DraftingFailed(f"The drafted template was not valid: {structure_errors}")
    title = parsed.title.strip()[:200] or "Imported station template"
    return DraftedTemplate(title=title, structure=structure)


def structure_from_imported(imported: ImportedTemplate) -> dict[str, Any]:
    """The stored template structure for a model's answer.

    Ids are made here from the labels, never taken from the model, so two
    headings with the same wording still get different ids. No block is marked
    required: the next document in the library may lack a heading this one has,
    and a required block would refuse it.
    """
    used_ids: set[str] = set()
    sections: list[dict[str, Any]] = []
    for imported_section in imported.sections:
        blocks = [
            _block_from_imported(imported_block, imported_section.audience, used_ids)
            for imported_block in imported_section.blocks
            if imported_block.label.strip()
        ]
        if not blocks:
            continue
        sections.append(
            {
                "id": _unique_id(imported_section.title, used_ids, fallback="section"),
                "title": imported_section.title.strip(),
                "audience": imported_section.audience,
                "blocks": blocks,
            }
        )
    return {"schemaVersion": 1, "layout": {"persona": imported.persona}, "sections": sections}


def _block_from_imported(imported_block: ImportedBlock, audience: str, used_ids: set[str]) -> dict[str, Any]:
    """One stored template block for a block the model described.

    A block in a faculty section is a faculty block whatever role the model
    gave it, unless it is debrief material, and a faculty or debrief block
    anywhere else would be hidden from the reader its section names, so the
    section decides. A table the model named no columns for is stored as a
    list, which needs none.
    """
    headings = [heading.strip() for heading in imported_block.fields if heading.strip()]
    column_keys: set[str] = set()
    fields = [
        {"key": _unique_id(column, column_keys, fallback="column"), "label": column} for column in headings
    ]
    block_type = imported_block.type if imported_block.type != "records" or fields else "list"
    role: str = imported_block.role
    if audience == "faculty":
        role = "debrief" if role == "debrief" else "faculty"
    elif role in ("faculty", "debrief"):
        role = "examiner" if audience == "examiner" else "hidden"
    block: dict[str, Any] = {
        "id": _unique_id(imported_block.label, used_ids, fallback="field"),
        "type": block_type,
        "role": role,
        "label": imported_block.label.strip(),
        "required": False,
    }
    if block_type == "records":
        block["fields"] = fields
    if block_type == "groupedList" and headings:
        block["groups"] = headings
    return block


def content_from_transcribed(structure: dict[str, Any], transcribed: TranscribedDocument) -> dict[str, Any]:
    """The station content for a model's answer: each block's value in the shape its type stores.

    A block the document had nothing for is left out. So is a value that
    cannot be stored as it stands: a select whose text is none of its options,
    a table cell under a column the template does not have.
    """
    answers = {block.block_id: block for block in transcribed.blocks}
    content: dict[str, Any] = {}
    for section in structure.get("sections") or []:
        for block in section.get("blocks") or []:
            answer = answers.get(str(block.get("id")))
            if answer is None:
                continue
            value = _stored_value(block, answer)
            if not is_empty(value):
                content[str(block["id"])] = value
    return content


def _stored_value(block: dict[str, Any], answer: TranscribedBlock) -> Any:
    """One block's value as its type stores it, or None for a type an import does not fill."""
    block_type = block.get("type")
    if block_type in ("shortText", "longText"):
        return answer.text.strip()
    if block_type == "singleSelect":
        wanted = answer.text.strip().lower()
        return next((option for option in block.get("options") or [] if str(option).lower() == wanted), None)
    if block_type == "list":
        return [item.strip() for item in answer.items if item.strip()]
    if block_type in ("records", "qaList"):
        if block_type == "qaList":
            keys = {"question", "answer"}
        else:
            keys = {str(field.get("key")) for field in block.get("fields") or [] if isinstance(field, dict)}
        rows = [
            {cell.key: cell.value.strip() for cell in row.cells if cell.key in keys and cell.value.strip()}
            for row in answer.rows
        ]
        return [row for row in rows if row and (block_type == "records" or "question" in row)]
    if block_type == "groupedList":
        groups = {
            group.name.strip(): [item.strip() for item in group.items if item.strip()]
            for group in answer.groups
            if group.name.strip()
        }
        return {name: items for name, items in groups.items() if items}
    return None


async def transcribe_station(
    source_text: str, structure: dict[str, Any], *, settings: Settings
) -> TranscribedStation:
    """Copy a document's words into a template's blocks.

    The model is asked again when its answer does not fit the template, with
    the validation errors, up to `MAX_ATTEMPTS` times. Raises
    `GenerationUnavailable` when no model can be reached and `DraftingFailed`
    when no attempt fits.
    """
    all_block_ids = sorted(collect_station_block_ids(structure))
    messages: list[dict[str, str]] = [
        {"role": "system", "content": _TRANSCRIBE_RULES},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "templateStructure": structure_spec(structure),
                    "allBlockIds": all_block_ids,
                    "document": source_text,
                }
            ),
        },
    ]
    # Two ways to run out of attempts: the model never answered, or it answered
    # and the answer never fitted. They are different things to tell the author.
    parse_error = ""
    fit_error: str | None = None
    for _attempt in range(MAX_ATTEMPTS):
        parsed, parse_error = await parse_ai_structured(
            messages, TranscribedDocument, settings=settings, log_prefix=LOG_PREFIX
        )
        if parsed is None:
            continue
        content = content_from_transcribed(structure, parsed)
        content_ok, content_errors = validate_station_content(structure, content)
        if content_ok:
            return TranscribedStation(title=parsed.title.strip(), content=content)
        fit_error = f"The draft did not fit the template: {content_errors}"
        messages.append({"role": "assistant", "content": json.dumps(parsed.model_dump(by_alias=True))})
        messages.append(
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "validationErrors": content_errors,
                        "instruction": (
                            "Your previous JSON failed validation. Return corrected JSON only, "
                            "still copying the document's words exactly."
                        ),
                    }
                ),
            }
        )
    if fit_error is None:
        raise GenerationUnavailable(parse_error or None)
    raise DraftingFailed(fit_error)


_NOT_ID_CHARACTERS = re.compile(r"[^a-z0-9]+")
_MAX_ID_LENGTH = 48


def _unique_id(label: str, used_ids: set[str], *, fallback: str) -> str:
    """A snake_case id for a label that no earlier block or section in this template has."""
    stem = _NOT_ID_CHARACTERS.sub("_", label.lower()).strip("_")[:_MAX_ID_LENGTH].strip("_") or fallback
    candidate = stem
    suffix = 2
    while candidate in used_ids:
        candidate = f"{stem}_{suffix}"
        suffix += 1
    used_ids.add(candidate)
    return candidate
