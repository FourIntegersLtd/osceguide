"""The text of an uploaded document: a PDF, or a Word `.docx` file.

Two slices read uploads into text before a model sees them: a CV, and a station
imported from somebody's existing library. Both need the same refusals — a file
that is not what its name says, a file built to be expensive to open — so the
reading lives here rather than in either slice.

Nothing here keeps the file. The caller stores the text and drops the bytes.
"""

from __future__ import annotations

import io
import zipfile
from collections.abc import Iterator
from xml.etree import ElementTree

PDF_SUFFIX = ".pdf"
DOCX_SUFFIX = ".docx"

# A PDF starts with this marker, give or take a few bytes of preamble some
# writers put in front of it. A file named `.pdf` without one is something else.
_PDF_MARKER = b"%PDF-"
_PDF_MARKER_WINDOW = 1024
# More pages than any CV or station has. Parsing is linear in pages and happens
# inside the request, so a thousand-page file is refused rather than read.
MAX_PDF_PAGES = 200

# A `.docx` is a zip archive; every zip starts with these two bytes.
_ZIP_MARKER = b"PK"
_DOCX_BODY_PATH = "word/document.xml"
# The body of a long station is well under a megabyte of XML. A small archive
# that unpacks to far more is a decompression bomb, refused before it is read.
MAX_DOCX_BODY_BYTES = 20 * 1024 * 1024

_WORD_NAMESPACE = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_PARAGRAPH = f"{_WORD_NAMESPACE}p"
_TABLE = f"{_WORD_NAMESPACE}tbl"
_TABLE_ROW = f"{_WORD_NAMESPACE}tr"
_TABLE_CELL = f"{_WORD_NAMESPACE}tc"
_TEXT_RUN = f"{_WORD_NAMESPACE}t"
_TAB = f"{_WORD_NAMESPACE}tab"
_LINE_BREAKS = frozenset({f"{_WORD_NAMESPACE}br", f"{_WORD_NAMESPACE}cr"})


class UnreadableDocument(Exception):
    """A file that could not be read as the kind of document its name says it is."""


def extract_text(filename: str, content: bytes) -> str:
    """The text of a PDF or `.docx` upload, chosen by the file's suffix."""
    lowered = filename.lower()
    if lowered.endswith(PDF_SUFFIX):
        return extract_pdf_text(content)
    if lowered.endswith(DOCX_SUFFIX):
        return extract_docx_text(content)
    raise UnreadableDocument("Only PDF and Word (.docx) files can be read.")


def extract_pdf_text(content: bytes) -> str:
    """The text of a PDF, page by page.

    `pypdf` is imported here rather than at the top so the API starts and serves
    every route that is not an upload on a machine without it — the same
    tolerance the LiveKit SDK is given.
    """
    if _PDF_MARKER not in content[:_PDF_MARKER_WINDOW]:
        raise UnreadableDocument("That file is not a PDF.")

    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(content))
        if len(reader.pages) > MAX_PDF_PAGES:
            raise UnreadableDocument(f"That PDF has more than {MAX_PDF_PAGES} pages.")
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except UnreadableDocument:
        raise
    except Exception as exc:  # noqa: BLE001 - a PDF pypdf cannot read is the person's problem, not a 500
        raise UnreadableDocument("That file could not be read as a PDF.") from exc


def extract_docx_text(content: bytes) -> str:
    """The text of a Word `.docx` file: its paragraphs and table rows, in document order.

    Read with the standard library rather than a Word package: the body is one
    XML file inside a zip, and the only things wanted from it are the words. A
    table row becomes one line with its cells separated by ` | `, so a mark
    scheme laid out as a table keeps each criterion next to its marks.
    """
    if not content.startswith(_ZIP_MARKER):
        raise UnreadableDocument("That file is not a Word (.docx) document.")
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            if archive.getinfo(_DOCX_BODY_PATH).file_size > MAX_DOCX_BODY_BYTES:
                raise UnreadableDocument("That Word document is too large to read.")
            body_xml = archive.read(_DOCX_BODY_PATH)
        # Word never writes a document type declaration. One in the body is an
        # attempt to make the parser expand entities, so it is refused unread.
        if b"<!DOCTYPE" in body_xml or b"<!ENTITY" in body_xml:
            raise UnreadableDocument("That file could not be read as a Word document.")
        root = ElementTree.fromstring(body_xml)  # noqa: S314 - declarations are refused above
    except UnreadableDocument:
        raise
    except Exception as exc:  # noqa: BLE001 - a broken archive is the person's problem, not a 500
        raise UnreadableDocument("That file could not be read as a Word document.") from exc

    lines: list[str] = []
    for container in root:
        lines.extend(_lines_in(container))
    return "\n".join(line for line in lines if line.strip())


def _lines_in(container: ElementTree.Element) -> Iterator[str]:
    """Each paragraph and table row directly inside one part of the document, in order."""
    for child in container:
        if child.tag == _PARAGRAPH:
            yield _paragraph_text(child)
        elif child.tag == _TABLE:
            for row in child.findall(_TABLE_ROW):
                cells = [" ".join(_lines_in(cell)).strip() for cell in row.findall(_TABLE_CELL)]
                yield " | ".join(cells)
        else:
            # Content controls and similar wrappers hold paragraphs of their own.
            yield from _lines_in(child)


def _paragraph_text(paragraph: ElementTree.Element) -> str:
    """One paragraph's words, with its tabs and manual line breaks kept as whitespace."""
    pieces: list[str] = []
    for node in paragraph.iter():
        if node.tag == _TEXT_RUN:
            pieces.append(node.text or "")
        elif node.tag == _TAB:
            pieces.append("\t")
        elif node.tag in _LINE_BREAKS:
            pieces.append("\n")
    return "".join(pieces)
