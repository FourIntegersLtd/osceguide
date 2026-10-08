"""Reading an uploaded station document, and the pure rules of an import.

The documents are built here byte by byte, a real PDF and a real Word file,
because the readers under test are what stand between an upload and a model.
"""

from __future__ import annotations

import io
import typing
import zipfile

import pytest
from osce_assessment.prompts.station import KNOWN_ROLES

from app.core.document_text import UnreadableDocument, extract_text
from app.features.stations import domain_imports
from app.features.stations.station_content import station_block_ids
from app.features.stations.station_import_drafting import (
    ImportedBlock,
    ImportedBlockRole,
    ImportedSection,
    ImportedTemplate,
    TranscribedBlock,
    TranscribedCell,
    TranscribedDocument,
    TranscribedGroup,
    TranscribedRow,
    content_from_transcribed,
    structure_from_imported,
)
from app.features.stations.station_validator import validate_station_structure
from tests.support.documents import a_pdf

_WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def docx(paragraphs: list[str], table_rows: list[list[str]] | None = None, *, prolog: str = "") -> bytes:
    """A minimal Word file: the given paragraphs, then an optional table."""
    body = "".join(f"<w:p><w:r><w:t>{paragraph}</w:t></w:r></w:p>" for paragraph in paragraphs)
    if table_rows:
        rows = "".join(
            "<w:tr>"
            + "".join(f"<w:tc><w:p><w:r><w:t>{cell}</w:t></w:r></w:p></w:tc>" for cell in row)
            + "</w:tr>"
            for row in table_rows
        )
        body += f"<w:tbl>{rows}</w:tbl>"
    document = (
        f'<?xml version="1.0" encoding="UTF-8"?>{prolog}'
        f'<w:document xmlns:w="{_WORD_NAMESPACE}"><w:body>{body}</w:body></w:document>'
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", document)
    return buffer.getvalue()


def test_a_pdf_is_read_by_its_suffix() -> None:
    assert "Chest pain station" in extract_text("Station 4.PDF", a_pdf("Chest pain station"))


def test_a_word_file_is_read_with_its_table_rows_kept_together() -> None:
    text = extract_text(
        "station.docx",
        docx(["Candidate instructions", "Take a history."], [["Introduces self", "1 mark"]]),
    )
    assert "Candidate instructions" in text
    assert "Take a history." in text
    assert "Introduces self | 1 mark" in text


def test_a_file_that_is_not_what_its_name_says_is_refused() -> None:
    with pytest.raises(UnreadableDocument):
        extract_text("station.pdf", b"plain text pretending to be a PDF")
    with pytest.raises(UnreadableDocument):
        extract_text("station.docx", b"plain text pretending to be a Word file")


def test_a_word_file_declaring_entities_is_refused() -> None:
    hostile = docx(["hello"], prolog='<!DOCTYPE w [<!ENTITY big "aaaaaaaaaa">]>')
    with pytest.raises(UnreadableDocument):
        extract_text("station.docx", hostile)


def test_only_pdf_and_word_files_pass_the_upload_check() -> None:
    domain_imports.validate_upload(filename="a.pdf", size=5000)
    domain_imports.validate_upload(filename="a.DOCX", size=5000)
    with pytest.raises(domain_imports.InvalidImport):
        domain_imports.validate_upload(filename="a.doc", size=5000)
    with pytest.raises(domain_imports.InvalidImport):
        domain_imports.validate_upload(filename="a.pdf", size=domain_imports.MAX_BYTES + 1)


def test_a_document_with_too_little_or_too_much_text_is_refused() -> None:
    with pytest.raises(domain_imports.InvalidImport):
        domain_imports.ensure_usable_text("a few words")
    with pytest.raises(domain_imports.InvalidImport):
        domain_imports.ensure_usable_text("x" * (domain_imports.MAX_TEXT_CHARS + 1))


def test_reworded_blocks_are_the_ones_whose_text_is_not_in_the_source() -> None:
    source = "Mr Khan is a 54-year-old\nteacher.  He says “it hurts” – often.\nIntroduces self | 1 mark"
    content = {
        "persona": 'Mr Khan is a 54-year-old teacher. He says "it hurts" - often.',
        "marks": ["Introduces self | 1 mark"],
        "history": "He has had chest pain for two days.",
        "more_marks": ["Introduces self | 1 mark", "Washes hands"],
    }
    assert domain_imports.reworded_block_ids(content, source) == ["history", "more_marks"]


def test_table_cells_and_grouped_items_are_each_compared_with_the_source() -> None:
    source = "Reaction\nHow did that feel?\nHR 72 BP 128/76\nA review post-\nstroke."
    content = {
        "states": [{"hr": "72", "bp": "128/76"}],
        "wrong_states": [{"hr": "72", "bp": "130/80"}],
        "debrief": {"Reaction": ["How did that feel?"]},
        "wrong_debrief": {"Reaction": ["How did that go?"]},
        "summary": "A review post-stroke.",
    }
    assert domain_imports.reworded_block_ids(content, source) == ["wrong_states", "wrong_debrief"]


def test_empty_blocks_are_named_in_template_order() -> None:
    structure = {
        "sections": [
            {"id": "one", "blocks": [{"id": "brief"}, {"id": "history"}]},
            {"id": "two", "blocks": [{"id": "marks"}]},
        ]
    }
    content = {"marks": [], "brief": "Take a history.", "history": ""}
    ordered = station_block_ids(structure)
    assert ordered == ["brief", "history", "marks"]
    assert domain_imports.empty_block_ids(ordered, content) == ["history", "marks"]


def test_a_station_takes_the_files_name_when_the_document_gave_no_title() -> None:
    assert domain_imports.station_title("  Chest pain  ", "station 4.pdf") == "Chest pain"
    assert domain_imports.station_title("", "station 4.pdf") == "station 4"


def test_a_station_may_be_drafted_only_once_there_is_a_template_and_no_draft_running() -> None:
    assert domain_imports.may_draft_station("template_ready", has_template=True)
    assert domain_imports.may_draft_station("failed", has_template=True)
    assert not domain_imports.may_draft_station("failed", has_template=False)
    assert not domain_imports.may_draft_station("drafting_station", has_template=True)
    assert not domain_imports.may_draft_station("completed", has_template=True)


def test_the_roles_an_import_may_use_are_the_roles_the_engine_knows() -> None:
    """A role added to the engine has to be offered to the import, or its blocks are never drafted."""
    assert set(typing.get_args(ImportedBlockRole)) == set(KNOWN_ROLES)


def test_a_drafted_template_gets_unique_ids_and_no_required_blocks() -> None:
    imported = ImportedTemplate(
        title="History station",
        persona="patient",
        sections=[
            ImportedSection(
                title="Notes",
                audience="candidate",
                blocks=[
                    ImportedBlock(label="Notes", type="longText", role="candidate_brief", fields=[]),
                    ImportedBlock(label="Notes", type="longText", role="candidate_brief", fields=[]),
                    ImportedBlock(label="  ", type="shortText", role="persona", fields=[]),
                ],
            ),
            ImportedSection(title="Empty", audience="examiner", blocks=[]),
            ImportedSection(
                title="Mark scheme!",
                audience="examiner",
                blocks=[ImportedBlock(label="Mark scheme!", type="list", role="examiner", fields=[])],
            ),
        ],
    )
    structure = structure_from_imported(imported)

    assert validate_station_structure(structure) == (True, [])
    assert structure["layout"] == {"persona": "patient"}
    assert [section["id"] for section in structure["sections"]] == ["notes_3", "mark_scheme_2"]
    assert [section["audience"] for section in structure["sections"]] == ["candidate", "examiner"]
    assert [block["id"] for block in structure["sections"][0]["blocks"]] == ["notes", "notes_2"]
    assert structure["sections"][1]["blocks"] == [
        {"id": "mark_scheme", "type": "list", "role": "examiner", "label": "Mark scheme!", "required": False}
    ]


def test_a_drafted_table_keeps_its_columns_and_a_faculty_section_makes_faculty_blocks() -> None:
    imported = ImportedTemplate(
        title="Simulation briefing",
        persona="patient",
        sections=[
            ImportedSection(
                title="Faculty",
                audience="faculty",
                blocks=[
                    ImportedBlock(
                        label="Resources", type="records", role="examiner", fields=["Item", "Linked document"]
                    ),
                    ImportedBlock(label="Debriefing points", type="groupedList", role="faculty", fields=[]),
                    ImportedBlock(label="Roles", type="records", role="faculty", fields=[]),
                ],
            ),
            ImportedSection(
                title="Patient",
                audience="patient",
                blocks=[ImportedBlock(label="Script", type="longText", role="faculty", fields=[])],
            ),
        ],
    )
    structure = structure_from_imported(imported)

    assert validate_station_structure(structure) == (True, [])
    faculty, patient = structure["sections"]
    assert [(block["type"], block["role"]) for block in faculty["blocks"]] == [
        ("records", "faculty"),
        ("groupedList", "faculty"),
        ("list", "faculty"),
    ]
    assert faculty["blocks"][0]["fields"] == [
        {"key": "item", "label": "Item"},
        {"key": "linked_document", "label": "Linked document"},
    ]
    # A faculty role outside a faculty section would hide the block from the patient it was filed for.
    assert patient["blocks"][0]["role"] == "hidden"


def _answer(block_id: str, **members: object) -> TranscribedBlock:
    """One block of a model's answer, with every member it did not use left empty."""
    return TranscribedBlock.model_validate(
        {"blockId": block_id, "text": "", "items": [], "rows": [], "groups": [], **members}
    )


def test_a_transcribed_answer_is_stored_in_the_shape_each_block_type_reads() -> None:
    structure = {
        "sections": [
            {
                "id": "patient",
                "blocks": [
                    {"id": "name", "type": "shortText"},
                    {"id": "gender", "type": "singleSelect", "options": ["male", "female"]},
                    {"id": "actions", "type": "list"},
                    {
                        "id": "states",
                        "type": "records",
                        "fields": [{"key": "hr", "label": "HR"}, {"key": "bp", "label": "BP"}],
                    },
                    {"id": "debrief", "type": "groupedList"},
                    {"id": "allergies", "type": "longText"},
                    {"id": "confidence", "type": "scale", "min": 1, "max": 5},
                ],
            }
        ]
    }
    transcribed = TranscribedDocument(
        title="Annual review",
        blocks=[
            _answer("name", text=" Samuel "),
            _answer("gender", text="Male"),
            _answer("actions", items=["Check blood pressure", " "]),
            _answer(
                "states",
                rows=[
                    TranscribedRow(
                        cells=[
                            TranscribedCell(key="hr", value="72"),
                            TranscribedCell(key="bp", value=""),
                            TranscribedCell(key="mood", value="calm"),
                        ]
                    ),
                    TranscribedRow(cells=[]),
                ],
            ),
            _answer("debrief", groups=[TranscribedGroup(name="Reaction", items=["How did that feel?"])]),
            _answer("allergies"),
            _answer("confidence", text="4"),
        ],
    )

    assert content_from_transcribed(structure, transcribed) == {
        "name": "Samuel",
        "gender": "male",
        "actions": ["Check blood pressure"],
        "states": [{"hr": "72"}],
        "debrief": {"Reaction": ["How did that feel?"]},
    }
