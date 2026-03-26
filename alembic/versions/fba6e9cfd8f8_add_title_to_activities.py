"""add_title_to_activities — safe idempotent revision

Revision ID: fba6e9cfd8f8
Revises: 9bcc008fefdb
Create Date: 2026-03-26 12:17:34.475098

PURPOSE:
  Adds the `title` column to the `activities` table, and confirms
  `deals.contact_id` is nullable. Uses idempotent checks to handle
  the case where columns already exist (e.g. after a partial migration
  or a rollback that left stale state).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


# revision identifiers, used by Alembic.
revision: str = 'fba6e9cfd8f8'
down_revision: Union[str, None] = '9bcc008fefdb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    insp = inspect(conn)
    return column in [c['name'] for c in insp.get_columns(table)]


def _cleanup_tmp_table(table: str) -> None:
    """Remove any stale Alembic temp table left over from a crashed migration."""
    tmp = f"_alembic_tmp_{table}"
    conn = op.get_bind()
    insp = inspect(conn)
    if tmp in insp.get_table_names():
        conn.execute(text(f'DROP TABLE "{tmp}"'))


def upgrade() -> None:
    # Clean up any stale temp tables from previous failed runs
    _cleanup_tmp_table('activities')
    _cleanup_tmp_table('deals')

    # ── 1. Add `title` column to activities (idempotent) ──────────────────
    if not _column_exists('activities', 'title'):
        with op.batch_alter_table('activities', schema=None) as batch_op:
            batch_op.add_column(sa.Column('title', sa.String(), nullable=True))

    # ── 2. Make deals.contact_id nullable (idempotent via batch rebuild) ───
    # NOTE: In SQLite, batch_alter_table always rebuilds the table.
    # The nullable change is cosmetic in SQLite (SQLite ignores NOT NULL
    # on existing rows), but we keep it for ORM alignment.
    # Only run this if the column currently exists — skip if already done.
    if _column_exists('deals', 'contact_id'):
        with op.batch_alter_table('deals', schema=None) as batch_op:
            batch_op.alter_column(
                'contact_id',
                existing_type=sa.INTEGER(),
                nullable=True
            )


def downgrade() -> None:
    _cleanup_tmp_table('deals')
    _cleanup_tmp_table('activities')

    if _column_exists('deals', 'contact_id'):
        with op.batch_alter_table('deals', schema=None) as batch_op:
            batch_op.alter_column(
                'contact_id',
                existing_type=sa.INTEGER(),
                nullable=False
            )

    if _column_exists('activities', 'title'):
        with op.batch_alter_table('activities', schema=None) as batch_op:
            batch_op.drop_column('title')
