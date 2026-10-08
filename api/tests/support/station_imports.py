"""Uploading a document to the station-import route."""

from __future__ import annotations

from uuid import UUID

from httpx import AsyncClient

from tests.support.documents import a_pdf
from tests.support.tokens import bearer

IMPORTS = "/api/v1/orgs/kings/station-imports"

COPIED = "Take a focused history from Mr Khan, who has had central chest pain for two days."
# Long enough to clear `MIN_TEXT_CHARS`, and containing `COPIED` word for word.
DOCUMENT = (
    f"Station 4. Chest pain. Candidate instructions. {COPIED} "
    "Patient history. You are Mr Khan, a 54-year-old teacher. The pain came on while marking. "
    "Mark scheme. Introduces self. Asks about the site of the pain. Asks about smoking."
)


def upload_import(
    client: AsyncClient,
    token: str,
    *,
    filename: str = "Station 4.pdf",
    content: bytes | None = None,
    template_version_id: UUID | None = None,
    url: str = IMPORTS,
):
    """Post one document to the import route, as a multipart form."""
    form = {"exam_code": "sca"}
    if template_version_id is not None:
        form["template_version_id"] = str(template_version_id)
    document = content if content is not None else a_pdf(DOCUMENT)
    files = {"file": (filename, document, "application/octet-stream")}
    return client.post(url, files=files, data=form, headers=bearer(token))
