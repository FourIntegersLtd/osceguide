"""Invoices an organisation pays against its purchase order (E-22).

The console raises them; the organisation's admin reads its own and quotes the
PO number its finance office needs before it will pay.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from app.features.billing import repository as billing_repo
from app.features.identity import repository as identity_repo
from app.features.tenancy import repository as tenancy_repo
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def an_org(client: AsyncClient, make_actor, slug: str = "kings") -> tuple[str, str, uuid.UUID]:  # type: ignore[no-untyped-def]
    """An organisation, a platform admin, and the organisation's own admin."""
    root = await make_actor(f"root-{slug}@osceguide.com", platform_admin=True)
    created = await client.post(
        "/api/v1/platform/organizations",
        json={"slug": slug, "name": f"{slug.title()} College", "org_type": "institution"},
        headers=bearer(root),
    )
    assert created.status_code == 201, created.text
    org_id = uuid.UUID(created.json()["id"])
    admin = await make_actor(
        f"admin-{slug}@example.com",
        memberships=(Membership(org_id=org_id, org_slug=slug, role="owner"),),
        active_org_slug=slug,
    )
    return root, admin, org_id


async def a_settled_payment(
    db_session: AsyncSession, org_id: uuid.UUID | None, currency: str = "gbp", plan_code: str = "sca_6m"
) -> uuid.UUID:
    """A bank transfer the console recorded, by a member of `org_id` (or of no organisation)."""
    payer = await identity_repo.create_user(
        session=db_session,
        email=f"payer-{uuid.uuid4().hex[:6]}@example.com",
        name="Payer",
        password_hash=None,
    )
    if org_id is not None:
        await tenancy_repo.add_membership(db_session, org_id=org_id, user_id=payer.id, role="trainee")
    plan = await billing_repo.create_plan(
        db_session,
        code=plan_code,
        stripe_price_id=f"price_{uuid.uuid4().hex[:6]}",
        amount_pence=4999,
        duration_days=180,
        exam_code="sca",
    )
    payment = await billing_repo.record_payment(
        db_session,
        user_id=payer.id,
        plan_id=plan.id,
        stripe_payment_intent_id=f"manual_{uuid.uuid4().hex[:8]}",
        checkout_session_id=None,
        amount_total_pence=4999,
        currency=currency,
        receipt_url=None,
        paid_at=datetime.now(UTC),
        entitlement_id=None,
    )
    payment_id = payment.id
    await db_session.commit()
    return payment_id


async def test_an_invoice_is_raised_numbered_and_read_by_the_org(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root, admin, org_id = await an_org(client, make_actor)
    payment_id = await a_settled_payment(db_session, org_id)

    created = await client.post(
        "/api/v1/platform/organizations/kings/invoices",
        json={
            "lines": [
                {"description": "Examiner training day", "quantity": 2, "unit_amount_pence": 30_000},
                {"payment_id": str(payment_id)},
            ]
        },
        headers=bearer(root),
    )
    assert created.status_code == 201, created.text
    invoice = created.json()
    assert re.fullmatch(r"INV-\d{4}-\d{6}", invoice["invoice_number"])
    assert invoice["customer_name"] == "Kings College"
    assert invoice["status"] == "issued"
    assert invoice["po_number"] is None
    assert invoice["total_pence"] == 60_000 + 4999
    assert [line["amount_pence"] for line in invoice["lines"]] == [60_000, 4999]
    assert invoice["lines"][1]["payment_id"] == str(payment_id)
    assert invoice["lines"][1]["description"].startswith("6-Month Access")

    second = await client.post(
        "/api/v1/platform/organizations/kings/invoices",
        json={"lines": [{"description": "Licence", "unit_amount_pence": 100}]},
        headers=bearer(root),
    )
    assert second.json()["invoice_number"] != invoice["invoice_number"]

    listed = await client.get("/api/v1/orgs/kings/invoices", headers=bearer(admin))
    assert listed.status_code == 200, listed.text
    assert {row["invoice_number"] for row in listed.json()["items"]} == {
        invoice["invoice_number"],
        second.json()["invoice_number"],
    }
    one = await client.get(f"/api/v1/orgs/kings/invoices/{invoice['id']}", headers=bearer(admin))
    assert one.json()["lines"] == invoice["lines"]


async def test_the_org_quotes_its_po_number_until_the_invoice_is_final(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    root, admin, _ = await an_org(client, make_actor)
    invoice = (
        await client.post(
            "/api/v1/platform/organizations/kings/invoices",
            json={"lines": [{"description": "Licence", "unit_amount_pence": 100}]},
            headers=bearer(root),
        )
    ).json()
    url = f"/api/v1/orgs/kings/invoices/{invoice['id']}/po-number"

    quoted = await client.put(url, json={"po_number": " PO-7781 "}, headers=bearer(admin))
    assert quoted.status_code == 200, quoted.text
    assert quoted.json()["po_number"] == "PO-7781"

    paid = await client.patch(
        f"/api/v1/platform/invoices/{invoice['id']}", json={"status": "paid"}, headers=bearer(root)
    )
    assert paid.json()["status"] == "paid"
    assert paid.json()["paid_at"] is not None

    refused = await client.put(url, json={"po_number": "PO-9999"}, headers=bearer(admin))
    assert refused.status_code == 409
    assert refused.json()["code"] == "invoice_not_editable"
    voided = await client.patch(
        f"/api/v1/platform/invoices/{invoice['id']}", json={"status": "void"}, headers=bearer(root)
    )
    assert voided.status_code == 409, "paid is final"


async def test_a_line_needs_an_amount_or_a_payment(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    root, _, _ = await an_org(client, make_actor)
    for line in ({"description": "Nothing to charge"}, {"payment_id": str(uuid.uuid4())}):
        refused = await client.post(
            "/api/v1/platform/organizations/kings/invoices", json={"lines": [line]}, headers=bearer(root)
        )
        assert refused.status_code == 422, refused.text
        assert refused.json()["code"] == "invalid_invoice_line"


async def test_one_org_cannot_read_anothers_invoices(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    root, _, _ = await an_org(client, make_actor, "kings")
    _, guys_admin, _ = await an_org(client, make_actor, "guys")
    invoice = (
        await client.post(
            "/api/v1/platform/organizations/kings/invoices",
            json={"lines": [{"description": "Licence", "unit_amount_pence": 100}]},
            headers=bearer(root),
        )
    ).json()

    assert (await client.get("/api/v1/orgs/guys/invoices", headers=bearer(guys_admin))).json()["items"] == []
    hidden = await client.get(f"/api/v1/orgs/guys/invoices/{invoice['id']}", headers=bearer(guys_admin))
    assert hidden.status_code == 404
    assert hidden.json()["code"] == "invoice_not_found"


async def test_only_the_console_raises_an_invoice(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin, _ = await an_org(client, make_actor)
    refused = await client.post(
        "/api/v1/platform/organizations/kings/invoices",
        json={"lines": [{"description": "Licence", "unit_amount_pence": 100}]},
        headers=bearer(admin),
    )
    assert refused.status_code == 403


async def test_an_unknown_organisation_cannot_be_invoiced(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root-none@osceguide.com", platform_admin=True)
    refused = await client.post(
        "/api/v1/platform/organizations/nobody/invoices",
        json={"lines": [{"description": "Licence", "unit_amount_pence": 100}]},
        headers=bearer(root),
    )
    assert refused.status_code == 404


async def test_a_line_bills_only_this_organisations_unbilled_payment_in_its_currency(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    # Otherwise one organisation's invoice could show another's customer and
    # plan, or bill the same transfer twice.
    root, _, org_id = await an_org(client, make_actor)
    outsider = await a_settled_payment(db_session, None, plan_code="sca_3m")
    in_euros = await a_settled_payment(db_session, org_id, currency="eur", plan_code="sca_12m")
    ours = await a_settled_payment(db_session, org_id)

    async def raise_for(payment_id: uuid.UUID) -> int:
        """Raise an invoice with one line billing this payment; answer the status."""
        response = await client.post(
            "/api/v1/platform/organizations/kings/invoices",
            json={"lines": [{"payment_id": str(payment_id)}]},
            headers=bearer(root),
        )
        return response.status_code

    assert await raise_for(ours) == 201
    for refused in (outsider, in_euros, ours):
        assert await raise_for(refused) == 422
