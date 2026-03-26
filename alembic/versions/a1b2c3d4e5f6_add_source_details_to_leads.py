"""add source_details to leads

Revision ID: a1b2c3d4e5f6
Revises: dc6fab398bad
Create Date: 2026-03-26 18:00:00.000000

PURPOSE:
  Adds the nullable `source_details` column to the leads table.
  Idempotent — safe to run on existing databases that already have leads.
  Does NOT modify any existing columns or constraints.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'dc6fab398bad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    return column in [c['name'] for c in inspect(conn).get_columns(table)]


def upgrade() -> None:
    if not _column_exists('leads', 'source_details'):
        with op.batch_alter_table('leads', schema=None) as batch_op:
            batch_op.add_column(
                sa.Column('source_details', sa.String(), nullable=True)
            )


def downgrade() -> None:
    if _column_exists('leads', 'source_details'):
        with op.batch_alter_table('leads', schema=None) as batch_op:
            batch_op.drop_column('source_details')
