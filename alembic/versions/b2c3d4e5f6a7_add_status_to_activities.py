"""add status to activities

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-26 19:00:00.000000

PURPOSE:
  Adds the nullable `status` column (default 'pending') to the activities table.
  Idempotent — safe to run on a database that already has activities.
  Does NOT touch any other table or column.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    return column in [c['name'] for c in inspect(conn).get_columns(table)]


def upgrade() -> None:
    if not _column_exists('activities', 'status'):
        with op.batch_alter_table('activities', schema=None) as batch_op:
            batch_op.add_column(
                sa.Column('status', sa.String(), nullable=True, server_default='pending')
            )


def downgrade() -> None:
    if _column_exists('activities', 'status'):
        with op.batch_alter_table('activities', schema=None) as batch_op:
            batch_op.drop_column('status')
