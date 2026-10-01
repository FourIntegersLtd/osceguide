"""Uploading a CV, reading it back, deleting it, and the job that structures it.

The upload parses the PDF in the request, so these tests build a real one —
a single-page Helvetica PDF assembled byte by byte, with a correct xref table,
because that is what `pypdf` reads. The model call is a background job and is
not run here; the two job paths that need no model — no API key configured, and
a row that has been deleted from under it — are exercised directly against the
session.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.core.document_text import extract_pdf_text
from app.core.settings import get_settings
from app.features.cv import domain, repository, service
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

CV = "/api/v1/cv"

# Long enough that the extracted text clears `MIN_TEXT_CHARS` and the assembled
# PDF clears `MIN_BYTES`, so the happy path is not tripped by either cheap check.
# A real CV's text is what makes the file big enough; the skeleton alone is not.
_BODY = (
    "Consultant orthopaedic surgeon with twelve years of clinical experience "
    "across trauma, elective and paediatric rotations. Published in peer-reviewed "
    "journals, led two quality-improvement audits, and taught undergraduates. "
) * 4


def _pdf(text: str) -> bytes:
    """A minimal one-page PDF carrying `text`, with a correct xref table."""
    safe = text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
    stream = f"BT /F1 12 Tf 72 720 Td ({safe}) Tj ET".encode("latin-1", "replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref_pos = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF".encode()
    return bytes(out)


def _upload(client: AsyncClient, token: str, *, filename: str = "My CV.pdf", content: bytes | None = None):  # type: ignore[no-untyped-def]
    files = {"file": (filename, content if content is not None else _pdf(_BODY), "application/pdf")}
    return client.post(CV, files=files, headers=bearer(token))


async def test_pypdf_reads_the_text_back_out_of_the_built_pdf() -> None:
    """A guard on the fixture itself: if this PDF stops parsing, every test below is meaningless."""
    assert len(_pdf(_BODY)) > domain.MIN_BYTES
    assert len(extract_pdf_text(_pdf(_BODY))) >= domain.MIN_TEXT_CHARS


async def test_uploading_a_cv_creates_a_processing_row(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("doctor@example.com")

    created = await _upload(client, token)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "processing"
    assert body["message"]

    listed = await client.get(CV, headers=bearer(token))
    assert listed.status_code == 200, listed.text
    assert listed.json()["total"] == 1
    assert listed.json()["cvs"][0]["original_filename"] == "My CV.pdf"


async def test_a_file_that_is_not_a_pdf_is_refused(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("doctor@example.com")

    refused = await _upload(client, token, filename="cv.docx", content=b"not a pdf at all" * 200)
    assert refused.status_code == 422, refused.text
    assert refused.json()["code"] == "invalid_cv_file"


async def test_a_pdf_with_nothing_to_read_is_refused(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("doctor@example.com")

    refused = await _upload(client, token, content=_pdf("hi"))
    assert refused.status_code == 422, refused.text
    assert refused.json()["code"] == "invalid_cv_file"


async def test_somebody_elses_cv_is_not_found(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    mine = await make_actor("doctor@example.com")
    theirs = await make_actor("other@example.com")

    cv_id = (await _upload(client, mine)).json()["id"]
    assert (await client.get(f"{CV}/{cv_id}", headers=bearer(mine))).status_code == 200

    probed = await client.get(f"{CV}/{cv_id}", headers=bearer(theirs))
    assert probed.status_code == 404, probed.text
    assert probed.json()["code"] == "cv_not_found"


async def test_the_job_records_a_failure_when_no_model_is_configured(db_session) -> None:  # type: ignore[no-untyped-def]
    """The one job path that needs no model: an unset key becomes the row's error.

    `OPENAI_API_KEY` is blanked in `conftest`, so this is the configured state of
    the test environment and the row must not sit in `processing` forever.
    """
    from datetime import UTC, datetime

    from app.features.identity import repository as identity_repository

    user = await identity_repository.create_user(
        db_session, email="doctor@example.com", name="Dr", password_hash=None
    )
    row = await repository.create(
        db_session, user_id=user.id, original_filename="CV.pdf", extracted_text="x" * 60
    )
    await db_session.flush()

    await service.run_extraction_job(db_session, row.id, settings=get_settings(), now=datetime.now(UTC))
    await db_session.flush()

    refreshed = await repository.get(db_session, row.id)
    assert refreshed is not None
    assert refreshed.status == domain.Status.FAILED.value
    assert refreshed.error and "OPENAI_API_KEY" in refreshed.error


async def test_the_job_tells_the_owner_the_read_finished(db_session) -> None:  # type: ignore[no-untyped-def]
    """`cv.read` is what lets `CvPanel` stop watching a row without polling it.

    The model call is unreachable here (no API key in the test environment), so
    this exercises the failure branch of the job — the row still settles, and
    the settling is still what the owner's `/me/events` stream should carry,
    whichever way the read ended.
    """
    from datetime import UTC, datetime

    from app.core.events import PENDING_KEY, user_topic
    from app.features.cv.service import CV_READ
    from app.features.identity import repository as identity_repository

    user = await identity_repository.create_user(
        db_session, email="cv-event@example.com", name="Dr", password_hash=None
    )
    row = await repository.create(
        db_session, user_id=user.id, original_filename="CV.pdf", extracted_text="x" * 60
    )
    await db_session.flush()

    await service.run_extraction_job(db_session, row.id, settings=get_settings(), now=datetime.now(UTC))

    assert (user_topic(user.id), CV_READ, {"cv_id": str(row.id)}) in db_session.info[PENDING_KEY]


async def test_the_job_leaves_an_already_finished_row_alone(db_session) -> None:  # type: ignore[no-untyped-def]
    """A redelivery must not overwrite a completed read."""
    from datetime import UTC, datetime

    from app.features.identity import repository as identity_repository

    user = await identity_repository.create_user(
        db_session, email="doctor@example.com", name="Dr", password_hash=None
    )
    row = await repository.create(
        db_session, user_id=user.id, original_filename="CV.pdf", extracted_text="x" * 60
    )
    await repository.mark_completed(db_session, row.id, structured={"summary": "done"}, at=datetime.now(UTC))
    await db_session.flush()

    await service.run_extraction_job(db_session, row.id, settings=get_settings(), now=datetime.now(UTC))
    await db_session.flush()

    refreshed = await repository.get(db_session, row.id)
    assert refreshed is not None
    assert refreshed.status == domain.Status.COMPLETED.value
    assert refreshed.structured == {"summary": "done"}


async def test_a_random_id_is_not_found(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("doctor@example.com")
    missing = await client.get(f"{CV}/{uuid.uuid4()}", headers=bearer(token))
    assert missing.status_code == 404
    assert missing.json()["code"] == "cv_not_found"


async def test_deleting_your_own_cv_takes_it_out_of_the_list(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("doctor@example.com")
    cv_id = (await _upload(client, token)).json()["id"]
    assert (await client.get(CV, headers=bearer(token))).json()["total"] == 1

    deleted = await client.delete(f"{CV}/{cv_id}", headers=bearer(token))
    assert deleted.status_code == 204, deleted.text

    listed = await client.get(CV, headers=bearer(token))
    assert listed.status_code == 200, listed.text
    assert listed.json()["total"] == 0
    assert listed.json()["cvs"] == []

    # Gone for the person who deleted it, not merely hidden from the list.
    reread = await client.get(f"{CV}/{cv_id}", headers=bearer(token))
    assert reread.status_code == 404, reread.text
    assert reread.json()["code"] == "cv_not_found"


async def test_deleting_somebody_elses_cv_is_not_found_and_leaves_it_alone(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor
) -> None:
    """A delete must not be a second way to probe an id, and must not reach the row."""
    mine = await make_actor("doctor@example.com")
    theirs = await make_actor("other@example.com")

    cv_id = (await _upload(client, mine)).json()["id"]

    probed = await client.delete(f"{CV}/{cv_id}", headers=bearer(theirs))
    assert probed.status_code == 404, probed.text
    assert probed.json()["code"] == "cv_not_found"

    # The refusal changed nothing: the owner's CV is still there to read.
    assert (await client.get(f"{CV}/{cv_id}", headers=bearer(mine))).status_code == 200
    assert (await client.get(CV, headers=bearer(mine))).json()["total"] == 1


async def test_deleting_a_random_id_is_not_found(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """The same answer as somebody else's, so the two cannot be told apart."""
    token = await make_actor("doctor@example.com")
    missing = await client.delete(f"{CV}/{uuid.uuid4()}", headers=bearer(token))
    assert missing.status_code == 404, missing.text
    assert missing.json()["code"] == "cv_not_found"


async def test_a_cv_still_being_read_can_be_deleted(client: AsyncClient, make_actor, db_session) -> None:  # type: ignore[no-untyped-def]
    """Deleting is allowed at `processing`, and the job then writes nothing back.

    The job is never run in these tests, so an uploaded CV is `processing` —
    asserted rather than assumed, because that is the state the delete has to
    accept. What must not happen is the read that is already in flight coming
    back and resurrecting a row the person has just removed.
    """
    from datetime import UTC, datetime

    token = await make_actor("doctor@example.com")
    created = await _upload(client, token)
    cv_id = uuid.UUID(created.json()["id"])
    assert created.json()["status"] == domain.Status.PROCESSING.value

    deleted = await client.delete(f"{CV}/{cv_id}", headers=bearer(token))
    assert deleted.status_code == 204, deleted.text
    assert await repository.get(db_session, cv_id) is None

    # The job, arriving now, finds no row and returns without calling a model.
    await service.run_extraction_job(db_session, cv_id, settings=get_settings(), now=datetime.now(UTC))
    await db_session.flush()

    # And a read that had already fetched the row before the delete lands has
    # nothing to update: it must not raise, and must not bring the CV back.
    await repository.mark_completed(
        db_session, cv_id, structured={"summary": "too late"}, at=datetime.now(UTC)
    )
    await db_session.flush()
    assert await repository.get(db_session, cv_id) is None
