"""What the tutor remembers about one learner

Three tables: what they read and practised, what the tutor wrote down about a
conversation or was told outright, and what a debrief concluded.

Revision ID: d8ca45c0932a
Revises: a4b5c6d7e8f9
Create Date: 2026-09-18 04:23:35.529186+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'd8ca45c0932a'
down_revision: str | None = 'a4b5c6d7e8f9'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('learning_events',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('exam_id', sa.Uuid(), nullable=True),
    sa.Column('kind', sa.String(length=16), nullable=False),
    sa.Column('ref_kind', sa.String(length=24), nullable=False),
    sa.Column('ref_id', sa.String(length=120), nullable=False),
    sa.Column('title', sa.String(length=300), nullable=False),
    sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('meta', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.CheckConstraint("kind IN ('viewed', 'practised', 'listened')", name=op.f('ck_learning_events_kind')),
    sa.CheckConstraint("ref_kind IN ('summary', 'slide_deck', 'podcast', 'blog', 'station', 'management_plan')", name=op.f('ck_learning_events_ref_kind')),
    sa.ForeignKeyConstraint(['exam_id'], ['exams.id'], name=op.f('fk_learning_events_exam_id_exams'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_learning_events_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_learning_events'))
    )
    op.create_index('ix_learning_events_dedup', 'learning_events', ['user_id', 'ref_kind', 'ref_id', 'occurred_at'], unique=False)
    op.create_index('ix_learning_events_user_time', 'learning_events', ['user_id', 'occurred_at'], unique=False)
    op.create_table('tutor_notes',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('exam_id', sa.Uuid(), nullable=True),
    sa.Column('session_id', sa.Uuid(), nullable=True),
    sa.Column('kind', sa.String(length=24), nullable=False),
    sa.Column('body', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.CheckConstraint("kind IN ('session_summary', 'stated_fact')", name=op.f('ck_tutor_notes_kind')),
    sa.ForeignKeyConstraint(['exam_id'], ['exams.id'], name=op.f('fk_tutor_notes_exam_id_exams'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['session_id'], ['assistant_sessions.id'], name=op.f('fk_tutor_notes_session_id_assistant_sessions'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_tutor_notes_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_tutor_notes'))
    )
    op.create_index('ix_tutor_notes_user_time', 'tutor_notes', ['user_id', 'created_at'], unique=False)
    op.create_table('debrief_summaries',
    sa.Column('attempt_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('exam_id', sa.Uuid(), nullable=True),
    sa.Column('key_insights', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('action_plan', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('narrative', sa.Text(), nullable=True),
    sa.Column('model_used', sa.String(length=64), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['attempt_id'], ['attempts.id'], name=op.f('fk_debrief_summaries_attempt_id_attempts'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['exam_id'], ['exams.id'], name=op.f('fk_debrief_summaries_exam_id_exams'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_debrief_summaries_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_debrief_summaries')),
    sa.UniqueConstraint('attempt_id', name='uq_debrief_summaries_attempt')
    )
    op.create_index('ix_debrief_summaries_user_time', 'debrief_summaries', ['user_id', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_debrief_summaries_user_time', table_name='debrief_summaries')
    op.drop_table('debrief_summaries')
    op.drop_index('ix_tutor_notes_user_time', table_name='tutor_notes')
    op.drop_table('tutor_notes')
    op.drop_index('ix_learning_events_user_time', table_name='learning_events')
    op.drop_index('ix_learning_events_dedup', table_name='learning_events')
    op.drop_table('learning_events')
