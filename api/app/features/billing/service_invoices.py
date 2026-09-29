"""Billing an organisation on an invoice, under its purchase order (E-22).

The console raises an invoice; the organisation's admin reads it and quotes
their PO number on it. A line may name a payment recorded through
`service_settlement` — typically a bank transfer entered in the console — and
then takes its amount and description from that payment unless told otherwise.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, raise_mapped
from app.core.tenancy import OrgNotFound
from app.features.billing import domain, errors, receipts, repository, repository_invoices
from app.features.billing.models import Invoice, InvoiceLine
from app.features.billing.schemas import (
    CreateInvoice,
    CreateInvoiceLine,
    InvoiceLineRead,
    InvoiceRead,
    UpdateInvoice,
)
from app.features.tenancy import service as tenancy

_REFUSALS: dict[type[Exception], type[AppError]] = {
    domain.InvoiceNotEditable: errors.InvoiceNotEditableError,
    domain.InvalidInvoiceLine: errors.InvalidInvoiceLineError,
}


async def create_invoice(
    session: AsyncSession, *, org_slug: str, body: CreateInvoice, actor_id: uuid.UUID, now: datetime
) -> InvoiceRead:
    """Raise an invoice for an organisation, numbered from the sequence.

    The organisation's name is copied onto it, as billed: renaming the
    organisation later must not change an invoice already sent.
    """
    org = await tenancy.org_ref_by_slug(session, org_slug)
    summary = await tenancy.org_ref_by_id(session, org.id) if org is not None else None
    if summary is None:
        raise OrgNotFound()
    try:
        lines = [await _line_values(session, line) for line in body.lines]
    except domain.InvalidInvoiceLine as exc:
        raise_mapped(exc, _REFUSALS)
    sequence = await repository_invoices.next_invoice_sequence(session)
    invoice = await repository_invoices.create_invoice(
        session,
        summary.id,
        lines=lines,
        invoice_number=domain.invoice_number(year=now.year, sequence=sequence),
        po_number=body.po_number,
        customer_name=summary.name,
        status=domain.INVOICE_ISSUED,
        currency=body.currency,
        total_pence=sum(line["amount_pence"] for line in lines),
        issued_at=now,
        due_at=body.due_at,
        notes=body.notes,
        created_by=actor_id,
    )
    return await _read(session, invoice)


async def list_invoices(
    session: AsyncSession, org_id: uuid.UUID, *, limit: int, cursor: dict[str, Any] | None
) -> tuple[list[InvoiceRead], str | None]:
    """A page of this organisation's invoices, most recent first, each with its lines."""
    invoices, next_cursor = await repository_invoices.list_invoices(
        session, org_id, limit=limit, cursor=cursor
    )
    lines = await repository_invoices.lines_for(session, [invoice.id for invoice in invoices])
    return [_invoice_read(invoice, lines[invoice.id]) for invoice in invoices], next_cursor


async def read_invoice(session: AsyncSession, org_id: uuid.UUID, invoice_id: uuid.UUID) -> InvoiceRead:
    """One of this organisation's invoices, or `invoice_not_found`."""
    return await _read(session, await _require(session, org_id, invoice_id))


async def set_po_number(
    session: AsyncSession, org_id: uuid.UUID, invoice_id: uuid.UUID, *, po_number: str, now: datetime
) -> InvoiceRead:
    """The organisation quoting its purchase order on an invoice it has not yet paid."""
    invoice = await _require(session, org_id, invoice_id)
    try:
        domain.ensure_po_editable(invoice.status)
    except domain.InvoiceNotEditable as exc:
        raise_mapped(exc, _REFUSALS)
    await repository_invoices.update_invoice(session, invoice.id, at=now, po_number=po_number.strip())
    return await read_invoice(session, org_id, invoice_id)


async def update_invoice(
    session: AsyncSession, invoice_id: uuid.UUID, *, changes: UpdateInvoice, now: datetime
) -> InvoiceRead:
    """The console marking an invoice paid or void, or correcting its PO number.

    Paid and void are final; a PO number changes only while it is issued.
    """
    invoice = await repository_invoices.any_invoice_by_id(session, invoice_id)
    if invoice is None:
        raise errors.InvoiceNotFound()
    values: dict[str, Any] = {}
    try:
        if changes.po_number is not None:
            domain.ensure_po_editable(invoice.status)
            values["po_number"] = changes.po_number.strip()
        if changes.status is not None and changes.status != invoice.status:
            domain.ensure_invoice_move(invoice.status, changes.status)
            values["status"] = changes.status
            if changes.status == domain.INVOICE_PAID:
                values["paid_at"] = now
            if changes.status == domain.INVOICE_VOID:
                values["voided_at"] = now
    except domain.InvoiceNotEditable as exc:
        raise_mapped(exc, _REFUSALS)
    if values:
        await repository_invoices.update_invoice(session, invoice.id, at=now, **values)
    return await read_invoice(session, invoice.org_id, invoice.id)


async def _line_values(session: AsyncSession, line: CreateInvoiceLine) -> dict[str, Any]:
    """The stored values for one requested line, filling blanks from its payment.

    A line naming a payment bills that payment's total unless an amount is
    given, and is described by the plan it bought unless a description is.
    """
    unit_amount = line.unit_amount_pence
    description = line.description
    if line.payment_id is not None:
        payment = await repository.payment_by_id(session, line.payment_id)
        if payment is None:
            raise domain.InvalidInvoiceLine("That payment does not exist.")
        if unit_amount is None:
            unit_amount = payment.amount_total_pence
        if description is None:
            plan = await repository.plan_by_id(session, payment.plan_id) if payment.plan_id else None
            label = receipts.plan_label(plan.code) if plan is not None else "Payment"
            description = f"{label} — {payment.receipt_id or payment.stripe_payment_intent_id}"
    if unit_amount is None or description is None:
        raise domain.InvalidInvoiceLine("A line needs a description and an amount, or a payment.")
    return {
        "description": description.strip(),
        "quantity": line.quantity,
        "unit_amount_pence": unit_amount,
        "amount_pence": domain.line_amount(quantity=line.quantity, unit_amount_pence=unit_amount),
        "payment_id": line.payment_id,
    }


async def _require(session: AsyncSession, org_id: uuid.UUID, invoice_id: uuid.UUID) -> Invoice:
    """One of this organisation's invoices, or `invoice_not_found`."""
    invoice = await repository_invoices.invoice_by_id(session, org_id, invoice_id)
    if invoice is None:
        raise errors.InvoiceNotFound()
    return invoice


async def _read(session: AsyncSession, invoice: Invoice) -> InvoiceRead:
    """One invoice with its lines, read afresh."""
    lines = await repository_invoices.lines_for(session, [invoice.id])
    return _invoice_read(invoice, lines[invoice.id])


def _invoice_read(invoice: Invoice, lines: list[InvoiceLine]) -> InvoiceRead:
    """Map a stored invoice and its lines onto what a route returns."""
    return InvoiceRead(
        id=invoice.id,
        org_id=invoice.org_id,
        invoice_number=invoice.invoice_number,
        po_number=invoice.po_number,
        customer_name=invoice.customer_name,
        status=invoice.status,
        currency=invoice.currency,
        total_pence=invoice.total_pence,
        issued_at=invoice.issued_at,
        due_at=invoice.due_at,
        paid_at=invoice.paid_at,
        voided_at=invoice.voided_at,
        notes=invoice.notes,
        lines=[
            InvoiceLineRead(
                position=line.position,
                description=line.description,
                quantity=line.quantity,
                unit_amount_pence=line.unit_amount_pence,
                amount_pence=line.amount_pence,
                payment_id=line.payment_id,
            )
            for line in lines
        ],
    )
