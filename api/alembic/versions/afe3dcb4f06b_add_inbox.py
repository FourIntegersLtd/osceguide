"""In-app messages: user_messages and who has read them. Additive: two new tables.

Revision ID: afe3dcb4f06b
Revises: z7a8b9c0d1e2
Create Date: 2026-10-07 19:45:31.543408+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "afe3dcb4f06b"
down_revision: str | None = "z7a8b9c0d1e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('user_messages',
    sa.Column('recipient_user_id', sa.Uuid(), nullable=True),
    sa.Column('sender_user_id', sa.Uuid(), nullable=True),
    sa.Column('kind', sa.String(length=32), nullable=False),
    sa.Column('subject', sa.String(length=200), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('station_flag_id', sa.Uuid(), nullable=True),
    sa.Column('site_message_id', sa.Uuid(), nullable=True),
    sa.Column('withdrawn_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("(kind = 'announcement') = (recipient_user_id IS NULL)", name=op.f('ck_user_messages_audience')),
    sa.CheckConstraint("kind IN ('report_answer', 'reply', 'note', 'announcement')", name=op.f('ck_user_messages_kind')),
    sa.ForeignKeyConstraint(['recipient_user_id'], ['users.id'], name=op.f('fk_user_messages_recipient_user_id_users'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['sender_user_id'], ['users.id'], name=op.f('fk_user_messages_sender_user_id_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['site_message_id'], ['site_messages.id'], name=op.f('fk_user_messages_site_message_id_site_messages'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['station_flag_id'], ['station_flags.id'], name=op.f('fk_user_messages_station_flag_id_station_flags'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_user_messages'))
    )
    op.create_index('ix_user_messages_announcements_created', 'user_messages', ['created_at', 'id'], unique=False, postgresql_where=sa.text('recipient_user_id IS NULL'))
    op.create_index('ix_user_messages_recipient_created', 'user_messages', ['recipient_user_id', 'created_at', 'id'], unique=False)
    op.create_table('user_message_reads',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('message_id', sa.Uuid(), nullable=False),
    sa.Column('read_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['message_id'], ['user_messages.id'], name=op.f('fk_user_message_reads_message_id_user_messages'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_user_message_reads_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'message_id', name=op.f('pk_user_message_reads'))
    )


def downgrade() -> None:
    op.drop_table('user_message_reads')
    op.drop_index('ix_user_messages_recipient_created', table_name='user_messages')
    op.drop_index('ix_user_messages_announcements_created', table_name='user_messages')
    op.drop_table('user_messages')
