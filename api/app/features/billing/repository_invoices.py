"""Storage for the invoices an organisation is billed. Org-scoped reads take `org_id` first."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import keyset_page
from app.features.billing import domain
from app.features.billing.models import INVOICE_NUMBER_SEQUENCE, Invoice, InvoiceLine


async def next_invoice_sequence(session: AsyncSession) -> int:
    """The next number from the invoice sequence, never handed out twice."""
    return int((await session.execute(select(INVOICE_NUMBER_SEQUENCE.next_value()))).scalar_one())


async def create_invoice(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    lines: list[dict[str, Any]],
    **values: Any,
) -> Invoice:
    """Write an invoice and its lines together, and return the invoice."""
    invoice = Invoice(org_id=org_id, **values)
    session.add(invoice)
    await session.flush()
    session.add_all(
        [InvoiceLine(invoice_id=invoice.id, position=position, **line) for position, line in enumerate(lines)]
    )
    await session.flush()
    await session.refresh(invoice)
    return invoice


async def invoice_by_id(session: AsyncSession, org_id: uuid.UUID, invoice_id: uuid.UUID) -> Invoice | None:
    """One of this organisation's invoices, or None."""
    stmt = select(Invoice).where(Invoice.org_id == org_id, Invoice.id == invoice_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def any_invoice_by_id(session: AsyncSession, invoice_id: uuid.UUID) -> Invoice | None:
    """Any organisation's invoice, for the platform console. Not org-scoped on purpose."""
    return (await session.execute(select(Invoice).where(Invoice.id == invoice_id))).scalar_one_or_none()


async def payment_is_invoiced(session: AsyncSession, payment_id: uuid.UUID) -> bool:
    """Whether a line on an invoice that is not void already bills this payment."""
    stmt = (
        select(InvoiceLine.id)
        .join(Invoice, Invoice.id == InvoiceLine.invoice_id)
        .where(InvoiceLine.payment_id == payment_id, Invoice.status != domain.INVOICE_VOID)
        .limit(1)
    )
    return (await session.execute(stmt)).first() is not None


async def lines_for(
    session: AsyncSession, invoice_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[InvoiceLine]]:
    """Each invoice's lines in order, in one query."""
    if not invoice_ids:
        return {}
    stmt = select(InvoiceLine).where(InvoiceLine.invoice_id.in_(invoice_ids)).order_by(InvoiceLine.position)
    lines: dict[uuid.UUID, list[InvoiceLine]] = {invoice_id: [] for invoice_id in invoice_ids}
    for line in (await session.execute(stmt)).scalars():
        lines[line.invoice_id].append(line)
    return lines


async def list_invoices(
    session: AsyncSession, org_id: uuid.UUID, *, limit: int, cursor: dict[str, Any] | None = None
) -> tuple[list[Invoice], str | None]:
    """A page of this organisation's invoices, most recently issued first."""
    stmt = select(Invoice).where(Invoice.org_id == org_id)
    return await keyset_page(
        session, stmt, sort_col=Invoice.issued_at, id_col=Invoice.id, limit=limit, cursor=cursor
    )


async def update_invoice(
    session: AsyncSession, invoice_id: uuid.UUID, *, at: datetime, **values: Any
) -> None:
    """Set the given columns on one invoice. The caller decides what may change."""
    await session.execute(update(Invoice).where(Invoice.id == invoice_id).values(updated_at=at, **values))
