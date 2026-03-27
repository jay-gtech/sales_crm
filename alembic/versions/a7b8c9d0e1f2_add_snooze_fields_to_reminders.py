"""add snooze fields to reminders — safe idempotent revision

Revision ID: a7b8c9d0e1f2
Revises: f1a2b3c4d5e6
Create Date: 2026-03-27 12:16:00.000000

PURPOSE:
  Adds last_shown_at (DateTime) and snooze_count (Integer, default 0)
  to the reminders table to support snooze/dismiss behavior.
  Idempotent — safe to run on existing databases.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    return column in [c['name'] for c in inspect(conn).get_columns(table)]


def upgrade() -> None:
    with op.batch_alter_table('reminders', schema=None) as batch_op:
        if not _column_exists('reminders', 'last_shown_at'):
            batch_op.add_column(
                sa.Column('last_shown_at', sa.DateTime(), nullable=True)
            )
        if not _column_exists('reminders', 'snooze_count'):
            batch_op.add_column(
                sa.Column('snooze_count', sa.Integer(), nullable=True, server_default='0')
            )


def downgrade() -> None:
    with op.batch_alter_table('reminders', schema=None) as batch_op:
        if _column_exists('reminders', 'snooze_count'):
            batch_op.drop_column('snooze_count')
        if _column_exists('reminders', 'last_shown_at'):
            batch_op.drop_column('last_shown_at')
