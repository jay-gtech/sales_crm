"""Add advanced lead fields — safe idempotent revision

Revision ID: c288b7015148
Revises: ccbfbf6f98f0
Create Date: 2026-03-26 10:15:25.884052

PURPOSE:
  Drops the legacy `notes` and `attachments` tables that were removed
  from the codebase. Uses conditional checks so the migration is safe
  to run even if those tables do not already exist (e.g. on clean installs
  where the initial migration never created them).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'c288b7015148'
down_revision: Union[str, None] = 'ccbfbf6f98f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table: str) -> bool:
    conn = op.get_bind()
    insp = inspect(conn)
    return table in insp.get_table_names()


def _index_exists(index_name: str, table: str) -> bool:
    conn = op.get_bind()
    insp = inspect(conn)
    return any(idx['name'] == index_name for idx in insp.get_indexes(table))


def upgrade() -> None:
    # ── Drop legacy `notes` table if it exists ────────────────────────────
    if _table_exists('notes'):
        with op.batch_alter_table('notes', schema=None) as batch_op:
            if _index_exists('ix_notes_id', 'notes'):
                batch_op.drop_index('ix_notes_id')
        op.drop_table('notes')

    # ── Drop legacy `attachments` table if it exists ──────────────────────
    if _table_exists('attachments'):
        with op.batch_alter_table('attachments', schema=None) as batch_op:
            if _index_exists('ix_attachments_id', 'attachments'):
                batch_op.drop_index('ix_attachments_id')
        op.drop_table('attachments')


def downgrade() -> None:
    # Restore attachments
    if not _table_exists('attachments'):
        op.create_table(
            'attachments',
            sa.Column('id', sa.INTEGER(), nullable=False),
            sa.Column('filename', sa.VARCHAR(), nullable=False),
            sa.Column('file_path', sa.VARCHAR(), nullable=False),
            sa.Column('file_type', sa.VARCHAR(), nullable=True),
            sa.Column('lead_id', sa.INTEGER(), nullable=True),
            sa.Column('contact_id', sa.INTEGER(), nullable=True),
            sa.Column('created_at', sa.DATETIME(), nullable=True),
            sa.ForeignKeyConstraint(['contact_id'], ['contacts.id'], ),
            sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('attachments', schema=None) as batch_op:
            batch_op.create_index('ix_attachments_id', ['id'], unique=False)

    # Restore notes
    if not _table_exists('notes'):
        op.create_table(
            'notes',
            sa.Column('id', sa.INTEGER(), nullable=False),
            sa.Column('content', sa.VARCHAR(), nullable=False),
            sa.Column('lead_id', sa.INTEGER(), nullable=True),
            sa.Column('contact_id', sa.INTEGER(), nullable=True),
            sa.Column('created_at', sa.DATETIME(), nullable=True),
            sa.ForeignKeyConstraint(['contact_id'], ['contacts.id'], ),
            sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('notes', schema=None) as batch_op:
            batch_op.create_index('ix_notes_id', ['id'], unique=False)
