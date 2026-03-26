"""integrate deals module — safe idempotent revision

Revision ID: ccbfbf6f98f0
Revises: e74884f5885c
Create Date: 2026-03-26 01:18:46.837791

PURPOSE:
  The initial migration (a457a9f724e2) already created the `deals` table
  with ix_deals_id and ix_deals_name. This revision handles columns that
  were added AFTER the initial migration (owner_id, lead_id, description,
  closing_date, follow_up_date, last_stage_change) and creates the
  deal_history table if it doesn't already exist.

  NOTE: index creation is SKIPPED here — they were created in the initial
  migration. Foreign key constraints in SQLite are advisory only (SQLite
  does not enforce them), so we just ensure the columns exist.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


# revision identifiers, used by Alembic.
revision: str = 'ccbfbf6f98f0'
down_revision: Union[str, None] = 'e74884f5885c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    """Return True if the column already exists in the table."""
    conn = op.get_bind()
    insp = inspect(conn)
    cols = [c['name'] for c in insp.get_columns(table)]
    return column in cols


def _table_exists(table: str) -> bool:
    conn = op.get_bind()
    insp = inspect(conn)
    return table in insp.get_table_names()


def _index_exists(index_name: str, table: str) -> bool:
    conn = op.get_bind()
    insp = inspect(conn)
    return any(idx['name'] == index_name for idx in insp.get_indexes(table))


def upgrade() -> None:
    # ── 1. Add missing columns to `deals` table (idempotent) ──────────────
    with op.batch_alter_table('deals', schema=None) as batch_op:
        if not _column_exists('deals', 'description'):
            batch_op.add_column(sa.Column('description', sa.String(), nullable=True))
        if not _column_exists('deals', 'closing_date'):
            batch_op.add_column(sa.Column('closing_date', sa.DateTime(), nullable=True))
        if not _column_exists('deals', 'follow_up_date'):
            batch_op.add_column(sa.Column('follow_up_date', sa.DateTime(), nullable=True))
        if not _column_exists('deals', 'last_stage_change'):
            batch_op.add_column(sa.Column('last_stage_change', sa.DateTime(), nullable=True))
        if not _column_exists('deals', 'owner_id'):
            batch_op.add_column(sa.Column('owner_id', sa.Integer(), nullable=True))
        if not _column_exists('deals', 'lead_id'):
            batch_op.add_column(sa.Column('lead_id', sa.Integer(), nullable=True))

    # ── 2. Create `deal_history` table if it doesn't exist ────────────────
    if not _table_exists('deal_history'):
        op.create_table(
            'deal_history',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('deal_id', sa.Integer(), nullable=False),
            sa.Column('old_stage', sa.String(), nullable=True),
            sa.Column('new_stage', sa.String(), nullable=False),
            sa.Column('changed_at', sa.DateTime(), nullable=True),
            sa.Column('changed_by_id', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['changed_by_id'], ['users.id'], ),
            sa.ForeignKeyConstraint(['deal_id'], ['deals.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_deal_history_id'), 'deal_history', ['id'], unique=False)

    # ── 3. NOTE: ix_deals_id and ix_deals_name already exist from the ──────
    #            initial migration. DO NOT recreate them here.


def downgrade() -> None:
    # Remove deal_history if we created it
    if _table_exists('deal_history'):
        op.drop_index(op.f('ix_deal_history_id'), table_name='deal_history')
        op.drop_table('deal_history')

    # Remove columns we added (batch_alter handles SQLite column removal)
    with op.batch_alter_table('deals', schema=None) as batch_op:
        for col in ['owner_id', 'lead_id', 'last_stage_change',
                    'follow_up_date', 'closing_date', 'description']:
            if _column_exists('deals', col):
                batch_op.drop_column(col)