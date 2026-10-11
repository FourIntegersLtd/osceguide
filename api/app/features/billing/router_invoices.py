"""Routes for invoices (E-22): the console raises and settles them, and the
organisation's admin reads them and quotes its PO number."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.db import SessionDep as Session
from app.core.errors import Forbidden, error_responses
from app.core.pagination import CursorParams, Page
from app.core.ports import ClockDep
from app.core.tenancy import OrgAdmin, OrgNotFound, PlatformAdmin
from app.features.billing import errors, schemas, service_invoices

router = APIRouter(tags=["billing"])


# Raise an invoice for an organisation; its number is assigned here.
@router.post(
    "/platform/organizations/{org_slug}/invoices",
    response_model=schemas.InvoiceRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Forbidden, OrgNotFound, errors.InvalidInvoiceLineError),
)
async def create_invoice(
    org_slug: str, body: schemas.CreateInvoice, admin: PlatformAdmin, session: Session, clock: ClockDep
) -> schemas.InvoiceRead:
    return await service_invoices.create_invoice(
        session, org_slug=org_slug, body=body, actor_id=admin.user_id, now=clock.now()
    )


# Mark an invoice paid or void, or correct its PO number while it is issued.
@router.patch(
    "/platform/invoices/{invoice_id}",
    response_model=schemas.InvoiceRead,
    responses=error_responses(Forbidden, errors.InvoiceNotFound, errors.InvoiceNotEditableError),
)
async def update_invoice(
    invoice_id: uuid.UUID,
    body: schemas.UpdateInvoice,
    admin: PlatformAdmin,
    session: Session,
    clock: ClockDep,
) -> schemas.InvoiceRead:
    _ = admin
    return await service_invoices.update_invoice(session, invoice_id, changes=body, now=clock.now())


# This organisation's invoices, most recently issued first.
@router.get(
    "/orgs/{org_slug}/invoices",
    response_model=Page[schemas.InvoiceRead],
    responses=error_responses(Forbidden),
)
async def list_invoices(
    workspace: OrgAdmin, session: Session, page: Annotated[CursorParams, Depends()]
) -> Page[schemas.InvoiceRead]:
    invoices, next_cursor = await service_invoices.list_invoices(
        session, workspace.org_id, limit=page.limit, cursor=page.cursor
    )
    return Page(items=invoices, next_cursor=next_cursor)


# One of this organisation's invoices, with its lines.
@router.get(
    "/orgs/{org_slug}/invoices/{invoice_id}",
    response_model=schemas.InvoiceRead,
    responses=error_responses(Forbidden, errors.InvoiceNotFound),
)
async def read_invoice(invoice_id: uuid.UUID, workspace: OrgAdmin, session: Session) -> schemas.InvoiceRead:
    return await service_invoices.read_invoice(session, workspace.org_id, invoice_id)


# Quote the organisation's purchase order number on an invoice it has not paid.
@router.put(
    "/orgs/{org_slug}/invoices/{invoice_id}/po-number",
    response_model=schemas.InvoiceRead,
    responses=error_responses(Forbidden, errors.InvoiceNotFound, errors.InvoiceNotEditableError),
)
async def set_invoice_po_number(
    invoice_id: uuid.UUID, body: schemas.SetPoNumber, workspace: OrgAdmin, session: Session, clock: ClockDep
) -> schemas.InvoiceRead:
    return await service_invoices.set_po_number(
        session, workspace.org_id, invoice_id, po_number=body.po_number, now=clock.now()
    )
