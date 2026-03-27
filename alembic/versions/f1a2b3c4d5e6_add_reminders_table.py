"""add reminders table — safe idempotent revision

Revision ID: f1a2b3c4d5e6
Revises: dc6fab398bad
Create Date: 2026-03-27 11:08:00.000000

PURPOSE:
  Creates the `reminders` table for the automatic follow-up reminder system.
  Fully standalone — no foreign keys to existing tables. Idempotent: skips
  creation if the table already exists.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    conn = op.get_bind()
    return table_name in inspect(conn).get_table_names()


def upgrade() -> None:
    if not _table_exists('reminders'):
        op.create_table(
            'reminders',
            sa.Column('id',            sa.Integer(),  primary_key=True, autoincrement=True),
            sa.Column('title',         sa.String(),   nullable=False),
            sa.Column('description',   sa.Text(),     nullable=True),
            sa.Column('related_type',  sa.String(),   nullable=True),
            sa.Column('related_id',    sa.Integer(),  nullable=True),
            sa.Column('reminder_time', sa.DateTime(), nullable=False),
            sa.Column('status',        sa.String(),   nullable=True, server_default='pending'),
            sa.Column('created_at',    sa.DateTime(), nullable=True, server_default=sa.func.now()),
        )
        op.create_index('ix_reminders_id', 'reminders', ['id'], unique=False)
        op.create_index('ix_reminders_status_time', 'reminders',
                        ['status', 'reminder_time'], unique=False)


def downgrade() -> None:
    if _table_exists('reminders'):
        op.drop_index('ix_reminders_status_time', table_name='reminders')
        op.drop_index('ix_reminders_id', table_name='reminders')
        op.drop_table('reminders')
