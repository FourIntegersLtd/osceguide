"""Invoices an organisation pays against a purchase order (E-22).

Nothing billed an institution: payments were card purchases by one person, or
payments entered in the console with no document to send a finance office.
An invoice has a number from its own sequence, the PO number the customer's
finance team quotes, and lines that may name the settled payment they bill for.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "3d7c790f920b"
down_revision: str | None = "40c4e90d0cd4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.schema.CreateSequence(sa.Sequence("invoice_number_seq")))
    op.create_table(
        "invoices",
        sa.Column("org_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_number", sa.String(length=32), nullable=False),
        sa.Column("po_number", sa.String(length=64), nullable=True),
        sa.Column("customer_name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=16), server_default=sa.text("'issued'"), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default=sa.text("'gbp'"), nullable=False),
        sa.Column("total_pence", sa.Integer(), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('issued', 'paid', 'void')", name=op.f("ck_invoices_ck_invoices_status")
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name=op.f("fk_invoices_created_by_users"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            name=op.f("fk_invoices_org_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_invoices")),
        sa.UniqueConstraint("invoice_number", name="uq_invoices_invoice_number"),
    )
    op.create_index("ix_invoices_org_issued", "invoices", ["org_id", "issued_at"], unique=False)
    op.create_table(
        "invoice_lines",
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=300), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_amount_pence", sa.Integer(), nullable=False),
        sa.Column("amount_pence", sa.Integer(), nullable=False),
        sa.Column("payment_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["invoices.id"],
            name=op.f("fk_invoice_lines_invoice_id_invoices"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["payment_id"],
            ["payments.id"],
            name=op.f("fk_invoice_lines_payment_id_payments"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_invoice_lines")),
        sa.UniqueConstraint("invoice_id", "position", name="uq_invoice_lines_invoice_position"),
    )


def downgrade() -> None:
    op.drop_table("invoice_lines")
    op.drop_index("ix_invoices_org_issued", table_name="invoices")
    op.drop_table("invoices")
    op.execute(sa.schema.DropSequence(sa.Sequence("invoice_number_seq")))
