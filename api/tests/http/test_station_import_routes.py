"""Importing a station from an uploaded PDF or Word document, over HTTP.

The upload reads the document in the request, so these tests send real files.
The two drafting steps are background jobs: each is run directly against the
session with the model call replaced, which is the only part that is not real.

One test per refusal, with the refusal last: a refused request rolls the test's
transaction back, taking the rows before it along.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from httpx import AsyncClient

from app.core.events import PENDING_KEY, user_topic
from app.core.settings import get_settings
from app.features.stations import service_imports
from app.features.stations.station_import_drafting import (
    ImportedBlock,
    ImportedSection,
    ImportedTemplate,
    TranscribedBlock,
    TranscribedDocument,
)
from tests.http.test_station_autogenerate_routes import org_with_admin, published_template_version
from tests.support.documents import a_pdf
from tests.support.station_imports import COPIED, DOCUMENT, IMPORTS, upload_import
from tests.support.tokens import bearer
from tests.unit.test_station_import_domain import docx

pytestmark = pytest.mark.db


_DRAFTED_TEMPLATE = ImportedTemplate(
    title="History taking station",
    persona="patient",
    sections=[
        ImportedSection(
            title="Candidate",
            audience="candidate",
            blocks=[
                ImportedBlock(
                    label="Candidate instructions", type="longText", role="candidate_brief", fields=[]
                )
            ],
        ),
        ImportedSection(
            title="Patient",
            audience="patient",
            blocks=[ImportedBlock(label="Patient history", type="longText", role="history", fields=[])],
        ),
        ImportedSection(
            title="Examiner",
            audience="examiner",
            blocks=[ImportedBlock(label="Mark scheme", type="list", role="examiner", fields=[])],
        ),
    ],
)


def _answer(block_id: str, *, text: str = "", items: list[str] | None = None) -> TranscribedBlock:
    """One block of a model's answer, with the members it did not use left empty."""
    return TranscribedBlock(blockId=block_id, text=text, items=items or [], rows=[], groups=[])


_TRANSCRIBED = TranscribedDocument(
    title="Chest pain",
    blocks=[
        _answer("candidate_instructions", text=COPIED),
        _answer("patient_history", text="A history the model made up."),
        _answer("mark_scheme"),
    ],
)


async def _draft_template(db_session, import_id: str) -> None:  # type: ignore[no-untyped-def]
    """Run the template job with the model answering `_DRAFTED_TEMPLATE`."""
    with patch(
        "app.features.stations.station_import_drafting.parse_ai_structured",
        new=AsyncMock(return_value=(_DRAFTED_TEMPLATE, "")),
    ):
        await service_imports.run_template_job(db_session, UUID(import_id), settings=get_settings())


async def _draft_station(db_session, import_id: str) -> None:  # type: ignore[no-untyped-def]
    """Run the station job with the model answering `_TRANSCRIBED`."""
    with patch(
        "app.features.stations.station_import_drafting.parse_ai_structured",
        new=AsyncMock(return_value=(_TRANSCRIBED, "")),
    ):
        await service_imports.run_station_job(db_session, UUID(import_id), settings=get_settings())


async def _station(client: AsyncClient, token: str, station_id: str) -> dict[str, object]:
    """One of the organisation's stations as its admin's list shows it, content included."""
    listed = await client.get("/api/v1/orgs/kings/stations", headers=bearer(token))
    assert listed.status_code == 200, listed.text
    return next(station for station in listed.json()["items"] if station["id"] == station_id)


async def test_a_pdf_becomes_a_template_draft_and_then_a_station_draft(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, db_session
) -> None:
    _, admin = await org_with_admin(client, make_actor)

    uploaded = await upload_import(client, admin)
    assert uploaded.status_code == 201, uploaded.text
    import_id = uploaded.json()["id"]
    assert uploaded.json()["status"] == "drafting_template"
    assert uploaded.json()["original_filename"] == "Station 4.pdf"

    await _draft_template(db_session, import_id)
    ready = (await client.get(f"{IMPORTS}/{import_id}", headers=bearer(admin))).json()
    assert ready["status"] == "template_ready"
    assert ready["station_id"] is None
    template_id = ready["template_id"]

    # The template is a draft the author reviews: nothing is built on it until it is published.
    published = await client.post(
        f"/api/v1/orgs/kings/station-templates/{template_id}/publish", headers=bearer(admin)
    )
    assert published.status_code == 200, published.text
    assert published.json()["id"] == ready["template_version_id"]
    assert [section["audience"] for section in published.json()["structure"]["sections"]] == [
        "candidate",
        "patient",
        "examiner",
    ]

    requested = await client.post(f"{IMPORTS}/{import_id}/station", headers=bearer(admin))
    assert requested.status_code == 200, requested.text
    assert requested.json()["status"] == "drafting_station"

    await _draft_station(db_session, import_id)
    done = (await client.get(f"{IMPORTS}/{import_id}", headers=bearer(admin))).json()
    assert done["status"] == "completed"
    assert done["error"] is None
    # The document had no text the model put in the mark scheme, and the
    # patient history is not the document's wording: both are named for review.
    assert done["empty_block_ids"] == ["mark_scheme"]
    assert done["reworded_block_ids"] == ["patient_history"]

    station = await _station(client, admin, done["station_id"])
    assert station["title"] == "Chest pain"
    assert station["status"] == "draft"
    assert station["template_version_id"] == ready["template_version_id"]
    assert station["content"] == {
        "candidate_instructions": COPIED,
        "patient_history": "A history the model made up.",
    }

    listed = (await client.get(IMPORTS, headers=bearer(admin))).json()
    assert [station_import["id"] for station_import in listed["imports"]] == [import_id]


async def test_a_word_file_with_a_published_template_goes_straight_to_a_station(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, db_session
) -> None:
    _, admin = await org_with_admin(client, make_actor)
    version_id = await published_template_version(client, admin)

    uploaded = await upload_import(
        client, admin, filename="Station 4.docx", content=docx([DOCUMENT]), template_version_id=version_id
    )
    assert uploaded.status_code == 201, uploaded.text
    assert uploaded.json()["status"] == "drafting_station"
    assert uploaded.json()["template_version_id"] == str(version_id)

    transcribed = TranscribedDocument(title="", blocks=[_answer("notes", text=COPIED)])
    with patch(
        "app.features.stations.station_import_drafting.parse_ai_structured",
        new=AsyncMock(return_value=(transcribed, "")),
    ):
        import_id = UUID(uploaded.json()["id"])
        await service_imports.run_station_job(db_session, import_id, settings=get_settings())

    done = (await client.get(f"{IMPORTS}/{uploaded.json()['id']}", headers=bearer(admin))).json()
    assert done["status"] == "completed"
    assert done["empty_block_ids"] == ["explanation"]
    assert done["reworded_block_ids"] == []
    # The document gave no title, so the station takes the file's name.
    assert (await _station(client, admin, done["station_id"]))["title"] == "Station 4"


async def test_a_job_with_no_model_configured_fails_the_import_and_tells_the_uploader(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, db_session
) -> None:
    """`OPENAI_API_KEY` is blanked in `conftest`, so the real model call is refused."""
    _, admin = await org_with_admin(client, make_actor)
    import_id = (await upload_import(client, admin)).json()["id"]
    db_session.info.pop(PENDING_KEY, None)

    await service_imports.run_template_job(db_session, UUID(import_id), settings=get_settings())

    # Read before the next request, whose commit sends what is queued.
    queued = list(db_session.info.get(PENDING_KEY, []))
    assert [(name, payload) for _topic, name, payload in queued] == [
        ("station_import.updated", {"import_id": import_id})
    ]
    assert queued[0][0].startswith(user_topic(""))

    failed = (await client.get(f"{IMPORTS}/{import_id}", headers=bearer(admin))).json()
    assert failed["status"] == "failed"
    assert failed["error"] == "The drafting service is not available right now. Try again in a few minutes."
    assert failed["template_id"] is None


async def test_a_redelivered_template_job_does_not_draft_a_second_template(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, db_session
) -> None:
    _, admin = await org_with_admin(client, make_actor)
    import_id = (await upload_import(client, admin)).json()["id"]

    await _draft_template(db_session, import_id)
    await _draft_template(db_session, import_id)

    templates = (await client.get("/api/v1/orgs/kings/station-templates", headers=bearer(admin))).json()
    assert [template["title"] for template in templates["items"]] == ["History taking station"]


async def test_a_station_is_refused_while_the_template_is_still_a_draft(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, db_session
) -> None:
    _, admin = await org_with_admin(client, make_actor)
    import_id = (await upload_import(client, admin)).json()["id"]
    await _draft_template(db_session, import_id)

    refused = await client.post(f"{IMPORTS}/{import_id}/station", headers=bearer(admin))
    assert refused.status_code == 409, refused.text
    assert refused.json()["code"] == "template_not_published"


async def test_a_station_is_refused_before_the_template_has_been_drafted(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor
) -> None:
    _, admin = await org_with_admin(client, make_actor)
    import_id = (await upload_import(client, admin)).json()["id"]

    refused = await client.post(f"{IMPORTS}/{import_id}/station", headers=bearer(admin))
    assert refused.status_code == 409, refused.text
    assert refused.json()["code"] == "import_not_ready"


async def test_a_file_that_is_not_a_pdf_or_word_document_is_refused(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)

    refused = await upload_import(client, admin, filename="station.txt", content=DOCUMENT.encode())
    assert refused.status_code == 422, refused.text
    assert refused.json()["code"] == "invalid_import_file"


async def test_a_document_with_nothing_to_read_is_refused(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)

    refused = await upload_import(client, admin, content=a_pdf("Scanned page"))
    assert refused.status_code == 422, refused.text
    assert refused.json()["code"] == "invalid_import_file"
    assert "too little text" in refused.json()["message"]


async def test_another_organisations_import_is_not_found(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    import_id = (await upload_import(client, admin)).json()["id"]
    _, outsider = await org_with_admin(client, make_actor, slug="barts")

    probed = await client.get(f"/api/v1/orgs/barts/station-imports/{import_id}", headers=bearer(outsider))
    assert probed.status_code == 404, probed.text
    assert probed.json()["code"] == "station_import_not_found"


async def test_a_platform_admin_imports_into_the_platform_library(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    root = await make_actor("root-imports@osceguide.com", platform_admin=True)

    uploaded = await upload_import(client, root, url="/api/v1/platform/station-imports")
    assert uploaded.status_code == 201, uploaded.text

    # The platform's import is not an organisation's to read.
    probed = await client.get(f"{IMPORTS}/{uploaded.json()['id']}", headers=bearer(admin))
    assert probed.status_code == 404, probed.text
