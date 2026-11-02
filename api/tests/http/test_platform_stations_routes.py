"""The platform authors its own library, through the same routes an org uses.

Until now the platform half of `stations` had no write path at all: the library
came from a legacy import or a hand-written row, and the shape of each exam's
stations lived in the engine as a formatter chosen by a branch on the exam's
code. These pin the two directions that matter — an org may build on what the
platform publishes, and neither side may author the other's content.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.core.auth import Membership
from tests.http.test_stations_routes import a_browser
from tests.support.catalog import create_exam
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

# A template whose blocks say what each is for. `role` is what the renderer
# places them by, which is what replaced the per-exam formatters.
TEMPLATE = {
    "schemaVersion": 1,
    "sections": [
        {
            "id": "main",
            "title": "Main",
            "blocks": [
                {
                    "id": "who_you_are",
                    "type": "longText",
                    "label": "Who you are",
                    "kind": "text",
                    "role": "persona",
                },
                {
                    "id": "why_you_came",
                    "type": "longText",
                    "label": "Why you came",
                    "kind": "text",
                    "role": "complaint",
                },
                {
                    "id": "expected_answers",
                    "type": "longText",
                    "label": "Expected answers",
                    "kind": "text",
                    "role": "examiner",
                },
            ],
        }
    ],
    "layout": {"persona": "patient"},
}

CONTENT = {
    "who_you_are": "Marek, 61, retired bus driver.",
    "why_you_came": "Short of breath walking to the shops.",
    "expected_answers": "Elicits the smoking history and offers cessation support.",
}


async def admin_token(make_actor) -> str:  # type: ignore[no-untyped-def]
    return await make_actor("admin@osceguide.com", platform_admin=True)


async def an_org(client: AsyncClient, make_actor, slug: str = "kings") -> uuid.UUID:  # type: ignore[no-untyped-def]
    root = await make_actor(f"root-{slug}@osceguide.com", platform_admin=True)
    response = await client.post(
        "/api/v1/platform/organizations",
        json={"slug": slug, "name": slug.title(), "org_type": "institution"},
        headers=bearer(root),
    )
    assert response.status_code == 201, response.text
    return uuid.UUID(response.json()["id"])


async def org_admin(make_actor, org_id: uuid.UUID, slug: str = "kings") -> str:  # type: ignore[no-untyped-def]
    return await make_actor(
        f"admin-{slug}@example.com",
        memberships=(Membership(org_id=org_id, org_slug=slug, role="admin"),),
        active_org_slug=slug,
    )


async def a_platform_template(client: AsyncClient, admin: str) -> str:
    created = await client.post(
        "/api/v1/platform/station-templates",
        json={"title": "Consultation", "exam_code": "sca", "structure": TEMPLATE},
        headers=bearer(admin),
    )
    assert created.status_code == 201, created.text
    published = await client.post(
        f"/api/v1/platform/station-templates/{created.json()['id']}/publish", headers=bearer(admin)
    )
    assert published.status_code == 200, published.text
    return str(published.json()["id"])


async def test_a_platform_admin_authors_and_publishes_a_library_station(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    admin = await admin_token(make_actor)
    await create_exam(client, admin, code="sca")
    template_version_id = await a_platform_template(client, admin)

    created = await client.post(
        "/api/v1/platform/stations",
        json={
            "title": "COPD exacerbation",
            "exam_code": "sca",
            "content": CONTENT,
            "template_version_id": template_version_id,
        },
        headers=bearer(admin),
    )
    assert created.status_code == 201, created.text
    assert created.json()["owner_kind"] == "platform"

    published = await client.post(
        f"/api/v1/platform/stations/{created.json()['id']}/versions/1/publish", headers=bearer(admin)
    )
    assert published.status_code == 200, published.text

    # And it is in the library every organisation draws on. Browsed as the
    # admin: the library is scoped to the exams a reader may open, and a
    # brand-new account holds none, so a fresh token would prove nothing about
    # whether the station was published.
    library = await client.get("/api/v1/stations", headers=bearer(admin))
    assert [s["title"] for s in library.json()["items"]] == ["COPD exacerbation"]


async def test_a_draft_library_station_is_not_in_the_library(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await admin_token(make_actor)
    await create_exam(client, admin, code="sca")
    await client.post(
        "/api/v1/platform/stations",
        json={"title": "Half written", "exam_code": "sca", "content": CONTENT},
        headers=bearer(admin),
    )

    library = await client.get("/api/v1/stations", headers=bearer(await make_actor("t@example.com")))
    mine = await client.get("/api/v1/platform/stations", headers=bearer(admin))

    assert library.json()["items"] == []
    assert [s["title"] for s in mine.json()["items"]] == ["Half written"], "its author still sees it"


async def a_published_library_station(client: AsyncClient, admin: str) -> str:
    """A platform station with version 1 published, returning the station's path."""
    created = await client.post(
        "/api/v1/platform/stations",
        json={"title": "COPD exacerbation", "exam_code": "sca", "content": CONTENT},
        headers=bearer(admin),
    )
    station_path = f"/api/v1/platform/stations/{created.json()['id']}"
    published = await client.post(f"{station_path}/versions/1/publish", headers=bearer(admin))
    assert published.status_code == 200, published.text
    return station_path


async def test_archiving_the_only_published_version_takes_a_station_out_of_the_library(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    # It used to stay listed, pointing at the archived version, so every
    # attempt a candidate started from the library was refused
    # `station_not_published`.
    admin = await admin_token(make_actor)
    await create_exam(client, admin, code="sca")
    station_path = await a_published_library_station(client, admin)

    archived = await client.post(f"{station_path}/versions/1/archive", headers=bearer(admin))
    assert archived.status_code == 200, archived.text

    library = await client.get("/api/v1/stations", headers=bearer(admin))
    assert library.json()["items"] == []


async def test_archiving_the_current_version_puts_the_previous_one_back_in_the_library(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    admin = await admin_token(make_actor)
    await create_exam(client, admin, code="sca")
    station_path = await a_published_library_station(client, admin)
    await client.post(f"{station_path}/versions", headers=bearer(admin))
    await client.post(f"{station_path}/versions/2/publish", headers=bearer(admin))

    await client.post(f"{station_path}/versions/2/archive", headers=bearer(admin))

    library = await client.get("/api/v1/stations", headers=bearer(admin))
    assert [(listed["title"], listed["version"]) for listed in library.json()["items"]] == [
        ("COPD exacerbation", 1)
    ]


async def test_a_freshly_published_station_is_hidden_until_an_editor_approves_it(
    client: AsyncClient, make_actor, db_session
) -> None:  # type: ignore[no-untyped-def]
    """Mirrors legacy b2c's `approved` flag: a published station is not yet in the library for
    a normal reader, only for the staff console curating it (`all_exams`)."""
    admin = await admin_token(make_actor)
    await create_exam(client, admin, code="sca")
    station_path = await a_published_library_station(client, admin)
    station_id = station_path.rsplit("/", 1)[-1]
    browser = await a_browser(db_session, make_actor, "reader@example.com")

    hidden = await client.get("/api/v1/stations", headers=bearer(browser))
    assert hidden.json()["items"] == []

    read_as_reader = await client.get(f"/api/v1/stations/{station_id}", headers=bearer(browser))
    assert read_as_reader.status_code == 404
    assert read_as_reader.json()["code"] == "station_not_found"

    staff_view = await client.get("/api/v1/stations", headers=bearer(admin))
    assert [s["title"] for s in staff_view.json()["items"]] == ["COPD exacerbation"]


async def test_approving_a_published_station_opens_it_to_every_reader(
    client: AsyncClient, make_actor, db_session
) -> None:  # type: ignore[no-untyped-def]
    admin = await admin_token(make_actor)
    await create_exam(client, admin, code="sca")
    station_path = await a_published_library_station(client, admin)
    browser = await a_browser(db_session, make_actor, "reader2@example.com")

    approved = await client.post(f"{station_path}/approve", headers=bearer(admin))
    assert approved.status_code == 200, approved.text
    assert approved.json()["approved"] is True

    now_visible = await client.get("/api/v1/stations", headers=bearer(browser))
    assert [s["title"] for s in now_visible.json()["items"]] == ["COPD exacerbation"]


async def test_approving_a_station_that_is_not_published_is_refused(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """A draft has no reader to protect yet, so there is nothing for the sign-off to act on."""
    admin = await admin_token(make_actor)
    await create_exam(client, admin, code="sca")
    created = await client.post(
        "/api/v1/platform/stations",
        json={"title": "Still drafting", "exam_code": "sca", "content": CONTENT},
        headers=bearer(admin),
    )
    station_path = f"/api/v1/platform/stations/{created.json()['id']}"

    refused = await client.post(f"{station_path}/approve", headers=bearer(admin))

    assert refused.status_code == 409, refused.text
    assert refused.json()["code"] == "station_not_approvable"


async def test_revoking_approval_pulls_a_published_station_back_out_of_the_library(
    client: AsyncClient, make_actor, db_session
) -> None:  # type: ignore[no-untyped-def]
    """Revoking touches only approval, never `status`: the version stays published, ready to be
    approved again once whatever was flagged is fixed."""
    admin = await admin_token(make_actor)
    await create_exam(client, admin, code="sca")
    station_path = await a_published_library_station(client, admin)
    await client.post(f"{station_path}/approve", headers=bearer(admin))
    browser = await a_browser(db_session, make_actor, "reader3@example.com")
    assert (await client.get("/api/v1/stations", headers=bearer(browser))).json()["items"] != []

    revoked = await client.post(f"{station_path}/revoke-approval", headers=bearer(admin))
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["approved"] is False
    assert revoked.json()["status"] == "published"

    hidden_again = await client.get("/api/v1/stations", headers=bearer(browser))
    assert hidden_again.json()["items"] == []

    staff_still_sees_it = await client.get("/api/v1/stations", headers=bearer(admin))
    assert [s["title"] for s in staff_still_sees_it.json()["items"]] == ["COPD exacerbation"]


async def test_an_org_admin_cannot_approve_a_platform_station(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await admin_token(make_actor)
    await create_exam(client, admin, code="sca")
    station_path = await a_published_library_station(client, admin)
    org_id = await an_org(client, make_actor, slug="guys")

    response = await client.post(
        f"{station_path}/approve", headers=bearer(await org_admin(make_actor, org_id, slug="guys"))
    )

    assert response.status_code == 403


async def test_approving_an_unknown_station_is_not_found(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await admin_token(make_actor)
    response = await client.post(f"/api/v1/platform/stations/{uuid.uuid4()}/approve", headers=bearer(admin))
    assert response.status_code == 404
    assert response.json()["code"] == "station_not_found"


async def test_an_org_admin_cannot_write_the_library(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await an_org(client, make_actor)
    response = await client.post(
        "/api/v1/platform/stations",
        json={"title": "Ours now", "exam_code": "sca", "content": CONTENT},
        headers=bearer(await org_admin(make_actor, org_id)),
    )
    assert response.status_code == 403


async def test_the_platform_station_list_filters_by_exam_code(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await admin_token(make_actor)
    await create_exam(client, admin, code="sca")
    await create_exam(client, admin, code="casc")
    await client.post(
        "/api/v1/platform/stations",
        json={"title": "COPD exacerbation", "exam_code": "sca", "content": CONTENT},
        headers=bearer(admin),
    )
    await client.post(
        "/api/v1/platform/stations",
        json={"title": "Low mood", "exam_code": "casc", "content": CONTENT},
        headers=bearer(admin),
    )

    response = await client.get(
        "/api/v1/platform/stations", params={"exam_code": "casc"}, headers=bearer(admin)
    )
    assert response.status_code == 200, response.text
    assert [s["title"] for s in response.json()["items"]] == ["Low mood"]


async def test_the_platform_station_list_excludes_archived_by_default(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    admin = await admin_token(make_actor)
    await create_exam(client, admin, code="sca")
    station_path = await a_published_library_station(client, admin)

    await client.post(f"{station_path}/versions/1/archive", headers=bearer(admin))

    default = await client.get("/api/v1/platform/stations", headers=bearer(admin))
    assert default.json()["items"] == []

    included = await client.get(
        "/api/v1/platform/stations", params={"include_archived": "true"}, headers=bearer(admin)
    )
    assert [s["title"] for s in included.json()["items"]] == ["COPD exacerbation"]


async def test_the_platform_template_list_filters_by_search_exam_and_published(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    admin = await admin_token(make_actor)
    await create_exam(client, admin, code="sca")
    await create_exam(client, admin, code="casc")

    sca_template = await client.post(
        "/api/v1/platform/station-templates",
        json={"title": "SCA consultation", "exam_code": "sca", "structure": TEMPLATE},
        headers=bearer(admin),
    )
    assert sca_template.status_code == 201, sca_template.text
    await client.post(
        f"/api/v1/platform/station-templates/{sca_template.json()['id']}/publish", headers=bearer(admin)
    )
    casc_template = await client.post(
        "/api/v1/platform/station-templates",
        json={"title": "CASC role-play", "exam_code": "casc", "structure": TEMPLATE},
        headers=bearer(admin),
    )
    assert casc_template.status_code == 201, casc_template.text
    unscoped_template = await client.post(
        "/api/v1/platform/station-templates",
        json={"title": "Generic form", "exam_code": None, "structure": TEMPLATE},
        headers=bearer(admin),
    )
    assert unscoped_template.status_code == 201, unscoped_template.text

    # `search` matches a title fragment.
    searched = await client.get(
        "/api/v1/platform/station-templates", params={"search": "consult"}, headers=bearer(admin)
    )
    assert [t["title"] for t in searched.json()["items"]] == ["SCA consultation"]

    # `exam_code` matches that exam plus every exam-agnostic template.
    scoped = await client.get(
        "/api/v1/platform/station-templates", params={"exam_code": "sca"}, headers=bearer(admin)
    )
    assert {t["title"] for t in scoped.json()["items"]} == {"SCA consultation", "Generic form"}

    # `published_only` keeps only the template with a published version.
    published = await client.get(
        "/api/v1/platform/station-templates", params={"published_only": "true"}, headers=bearer(admin)
    )
    assert [t["title"] for t in published.json()["items"]] == ["SCA consultation"]


async def test_an_org_builds_its_own_station_on_a_platform_template(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """The shape is shared downward; the content stays the institution's own."""
    admin = await admin_token(make_actor)
    await create_exam(client, admin, code="sca")
    template_version_id = await a_platform_template(client, admin)
    org_id = await an_org(client, make_actor)

    response = await client.post(
        "/api/v1/orgs/kings/stations",
        json={
            "title": "Our own case",
            "exam_code": "sca",
            "content": CONTENT,
            "template_version_id": template_version_id,
        },
        headers=bearer(await org_admin(make_actor, org_id)),
    )

    assert response.status_code == 201, response.text
    assert response.json()["owner_kind"] == "org"


async def test_an_org_cannot_edit_a_platform_template(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await admin_token(make_actor)
    await create_exam(client, admin, code="sca")
    created = await client.post(
        "/api/v1/platform/station-templates",
        json={"title": "Consultation", "exam_code": "sca", "structure": TEMPLATE},
        headers=bearer(admin),
    )
    org_id = await an_org(client, make_actor)

    response = await client.patch(
        f"/api/v1/orgs/kings/station-templates/{created.json()['id']}/versions/1",
        json={"structure": {"blocks": []}},
        headers=bearer(await org_admin(make_actor, org_id)),
    )

    assert response.status_code == 404


async def test_a_platform_admin_is_not_thereby_an_org_admin(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Deliberate: `OrgAdmin` sets allow_platform_admin=False."""
    await an_org(client, make_actor)  # the org exists; the admin still is not its admin
    admin = await admin_token(make_actor)
    await create_exam(client, admin, code="sca")

    response = await client.post(
        "/api/v1/orgs/kings/stations",
        json={"title": "Theirs now", "exam_code": "sca", "content": CONTENT},
        headers=bearer(admin),
    )

    assert response.status_code == 403


async def test_a_platform_station_is_fact_checked_beside_its_content_and_ruled_on(
    client: AsyncClient, make_actor, db_session
) -> None:  # type: ignore[no-untyped-def]
    import json

    from app.core.ports import GuidelinePassage
    from app.features.identity import repository as identity_repository
    from app.features.stations.service_facts import run_check, save_progress
    from tests.support.fakes import FakeGuidelineIndex, FakeGuidelineWeb

    admin = await admin_token(make_actor)
    user = await identity_repository.user_by_email(db_session, "admin@osceguide.com")
    assert user is not None
    user_id = user.id
    await create_exam(client, admin, code="sca")
    created = await client.post(
        "/api/v1/platform/stations",
        json={"title": "COPD", "exam_code": "sca", "content": CONTENT, "template_version_id": None},
        headers=bearer(admin),
    )
    assert created.status_code == 201, created.text
    version_path = f"/api/v1/platform/stations/{created.json()['id']}/versions/1"

    queued = await client.post(f"{version_path}/check-facts", headers=bearer(admin))
    assert queued.status_code == 202, queued.text
    assert queued.json() == {
        "checking": True,
        "producing": False,
        "facts": None,
        "error": None,
        "brief": None,
        "run": None,
    }
    again = await client.post(f"{version_path}/check-facts", headers=bearer(admin))
    assert again.json()["code"] == "fact_check_running"

    def model(prompt: str) -> str:
        if "List the clinical claims" in prompt:
            claim = {"section": 1, "claim": "Smokers are offered cessation support", "question": "q"}
            return json.dumps({"claims": [claim]})
        return json.dumps(
            {
                "verdict": "contradicted",
                "evidence": 1,
                "quote": "refer to a stop smoking service",
                "why": "NICE says refer.",
                "line": 1,
                "new": "Elicits the smoking history and refers to a stop smoking service.",
            }
        )

    passage = GuidelinePassage(source="NICE NG209", text="Refer to a stop smoking service.", score=0.9)
    version_id = uuid.UUID(await _version_id(client, admin, created.json()["id"]))
    seen_while_running: list[tuple[bool, dict[str, int], int]] = []

    async def progress(facts: dict[str, object]) -> None:
        await save_progress(db_session, version_id, requested_by=user_id, facts=facts)
        running = (await client.get(f"{version_path}/review", headers=bearer(admin))).json()
        seen_while_running.append(
            (running["checking"], running["facts"]["progress"], len(running["facts"]["claims"]))
        )

    await run_check(
        db_session,
        version_id,
        requested_by=user_id,
        guidelines=FakeGuidelineIndex([passage]),
        web=FakeGuidelineWeb(None),
        complete=model,
        progress=progress,
    )
    assert seen_while_running == [(True, {"done": 0, "total": 1}, 0), (True, {"done": 1, "total": 1}, 1)]

    review = (await client.get(f"{version_path}/review", headers=bearer(admin))).json()
    assert review["checking"] is False
    assert "progress" not in review["facts"]
    [claim] = review["facts"]["claims"]
    assert (claim["field"], claim["place"], claim["verdict"]) == (
        "expected_answers",
        "Expected answers",
        "contradicted",
    )
    assert claim["suggestion"] == {
        "old": "Elicits the smoking history and offers cessation support.",
        "new": "Elicits the smoking history and refers to a stop smoking service.",
    }

    corrected = {
        **CONTENT,
        "expected_answers": "Elicits the smoking history and refers to a stop smoking service.",
    }
    ruled = {**review["facts"], "claims": [{**claim, "decision": "accepted"}]}
    saved = await client.patch(
        version_path, json={"content": corrected, "facts": ruled}, headers=bearer(admin)
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["content"] == corrected
    assert "review" not in saved.json()
    reread = (await client.get(f"{version_path}/review", headers=bearer(admin))).json()
    assert reread["facts"]["claims"][0]["decision"] == "accepted"


async def _version_id(client: AsyncClient, admin: str, station_id: str) -> str:
    versions = await client.get(f"/api/v1/stations/{station_id}/versions", headers=bearer(admin))
    return str(versions.json()[0]["id"])


DRAFTED = {
    **CONTENT,
    "expected_answers": "Elicits the smoking history and offers nicotine gum only.",
}


async def _producing_station(client: AsyncClient, admin: str) -> tuple[str, str]:
    """A blank platform station on a template, set to be produced; its id and version path."""
    await create_exam(client, admin, code="sca")
    template_version_id = await a_platform_template(client, admin)
    created = await client.post(
        "/api/v1/platform/stations",
        json={"title": "COPD", "exam_code": "sca", "content": {}, "template_version_id": template_version_id},
        headers=bearer(admin),
    )
    assert created.status_code == 201, created.text
    station_id = str(created.json()["id"])
    version_path = f"/api/v1/platform/stations/{station_id}/versions/1"
    started = await client.post(
        f"{version_path}/produce",
        json={"brief": "Breathless smoker, COPD diagnosis. Mr B, 64, coughs."},
        headers=bearer(admin),
    )
    assert started.status_code == 202, started.text
    assert (started.json()["producing"], started.json()["run"]["steps"]) == (True, [])
    assert started.json()["brief"] == {"brief": "Breathless smoker, COPD diagnosis. Mr B, 64, coughs."}
    return station_id, version_path


async def test_the_agent_drafts_a_station_fixes_what_the_sources_contradict_and_leaves_a_draft(
    client: AsyncClient, make_actor, db_session
) -> None:  # type: ignore[no-untyped-def]
    from app.features.identity import repository as identity_repository
    from app.features.media_production.service_produce import STATION, run_produce_job
    from tests.support.produce_kit import answering, one_session, produce_kit

    admin = await admin_token(make_actor)
    station_id, version_path = await _producing_station(client, admin)
    user = await identity_repository.user_by_email(db_session, "admin@osceguide.com")
    assert user is not None
    version_id = uuid.UUID(await _version_id(client, admin, station_id))
    run_id = (await client.get(f"{version_path}/review", headers=bearer(admin))).json()["run"]["id"]

    # Code drafts, checks and hands over; the model only rules on the contradiction.
    turn, asked = answering(
        {"rule": [{"decision": "accept", "reason": "Gum alone is not enough."}]}, tokens=50
    )
    kit, record = produce_kit(DRAFTED, wrong={"offers nicotine gum only": "refers to a stop smoking service"})
    await run_produce_job(
        version_id,
        requested_by=user.id,
        run_id=run_id,
        sessions=one_session(db_session),
        target=STATION,
        turn=turn,
        kit=kit,
    )

    assert [tool for tool, _ in asked] == ["rule"]
    assert "Mr B, 64, coughs." in record.drafts[0]
    review = (await client.get(f"{version_path}/review", headers=bearer(admin))).json()
    assert review["producing"] is False
    assert review["run"]["outcome"] == "finished"
    assert [step["tool"] for step in review["run"]["steps"]] == [
        "write_draft",
        "check_facts",
        "rule_claim",
        "finish",
    ]
    assert "1 contradicted" in review["run"]["steps"][1]["summary"]
    assert review["run"]["open"] == ["Review the claims in the fact check: 1 corrected by the agent."]
    [claim] = review["facts"]["claims"]
    assert (claim["field"], claim["decision"], claim["by"]) == ("expected_answers", "accepted", "agent")
    versions = await client.get(f"/api/v1/stations/{station_id}/versions", headers=bearer(admin))
    content = versions.json()[0]["content"]
    assert content == {
        **CONTENT,
        "expected_answers": "Elicits the smoking history and refers to a stop smoking service.",
    }


async def test_a_station_being_produced_is_not_edited_checked_or_produced_again(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    admin = await admin_token(make_actor)
    _, version_path = await _producing_station(client, admin)

    stopped = await client.post(f"{version_path}/stop-produce", headers=bearer(admin))
    assert (stopped.status_code, stopped.json()["run"]["stop"]) == (202, True)
    again = await client.post(
        f"{version_path}/produce", json={"brief": "Another go at it."}, headers=bearer(admin)
    )
    assert again.json()["code"] == "station_being_produced"
    checked = await client.post(f"{version_path}/check-facts", headers=bearer(admin))
    assert checked.json()["code"] == "station_being_produced"
    edited = await client.patch(version_path, json={"content": CONTENT}, headers=bearer(admin))
    assert edited.json()["code"] == "station_being_produced"


async def test_a_station_without_a_template_is_not_produced(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await admin_token(make_actor)
    await create_exam(client, admin, code="sca")
    created = await client.post(
        "/api/v1/platform/stations",
        json={"title": "COPD", "exam_code": "sca", "content": CONTENT, "template_version_id": None},
        headers=bearer(admin),
    )
    response = await client.post(
        f"/api/v1/platform/stations/{created.json()['id']}/versions/1/produce",
        json={"brief": "Breathless smoker."},
        headers=bearer(admin),
    )
    assert response.json()["code"] == "station_has_no_template"


# --------------------------------------------------------------------------
# Removing an unwanted draft, and one draft at a time
# --------------------------------------------------------------------------


async def a_library_draft(client: AsyncClient, admin: str, title: str = "Half written") -> str:
    created = await client.post(
        "/api/v1/platform/stations",
        json={"title": title, "exam_code": "sca", "content": CONTENT},
        headers=bearer(admin),
    )
    assert created.status_code == 201, created.text
    return f"/api/v1/platform/stations/{created.json()['id']}"


async def test_a_platform_admin_deletes_a_single_version_draft_and_the_station_goes_with_it(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    admin = await admin_token(make_actor)
    await create_exam(client, admin, code="sca")
    station_path = await a_library_draft(client, admin)

    deleted = await client.delete(f"{station_path}/versions/1", headers=bearer(admin))

    assert deleted.status_code == 204, deleted.text
    mine = await client.get("/api/v1/platform/stations?include_archived=true", headers=bearer(admin))
    assert mine.json()["items"] == []


async def test_deleting_a_draft_leaves_the_station_and_its_published_version(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    admin = await admin_token(make_actor)
    await create_exam(client, admin, code="sca")
    station_path = await a_published_library_station(client, admin)
    await client.post(f"{station_path}/versions", headers=bearer(admin))

    deleted = await client.delete(f"{station_path}/versions/2", headers=bearer(admin))

    assert deleted.status_code == 204, deleted.text
    library = await client.get("/api/v1/stations", headers=bearer(admin))
    assert [(s["title"], s["version"]) for s in library.json()["items"]] == [("COPD exacerbation", 1)]


async def test_a_published_library_version_is_not_deleted(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await admin_token(make_actor)
    await create_exam(client, admin, code="sca")
    station_path = await a_published_library_station(client, admin)

    refused = await client.delete(f"{station_path}/versions/1", headers=bearer(admin))

    assert refused.status_code == 409
    assert refused.json()["code"] == "not_deletable"


async def test_deleting_an_unknown_library_version_is_not_found(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await admin_token(make_actor)
    await create_exam(client, admin, code="sca")
    station_path = await a_library_draft(client, admin)

    missing = await client.delete(f"{station_path}/versions/9", headers=bearer(admin))

    assert missing.status_code == 404
    assert missing.json()["code"] == "version_not_found"


async def test_only_a_platform_admin_deletes_a_library_draft(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await admin_token(make_actor)
    await create_exam(client, admin, code="sca")
    station_path = await a_library_draft(client, admin)
    org_id = await an_org(client, make_actor)
    outsider = await org_admin(make_actor, org_id)

    refused = await client.delete(f"{station_path}/versions/1", headers=bearer(outsider))

    assert refused.status_code == 403


async def test_a_second_draft_is_refused_while_one_is_open(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await admin_token(make_actor)
    await create_exam(client, admin, code="sca")
    station_path = await a_library_draft(client, admin)

    refused = await client.post(f"{station_path}/versions", headers=bearer(admin))

    assert refused.status_code == 409
    assert refused.json()["code"] == "draft_exists"
    assert "v1 is still a draft" in refused.json()["message"]


async def test_a_new_draft_is_allowed_once_the_open_one_is_published(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await admin_token(make_actor)
    await create_exam(client, admin, code="sca")
    station_path = await a_published_library_station(client, admin)

    created = await client.post(f"{station_path}/versions", headers=bearer(admin))

    assert created.status_code == 201, created.text
    assert created.json()["version"] == 2
