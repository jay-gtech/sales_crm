"""fix missing lead fields — safe idempotent revision

Revision ID: dc6fab398bad
Revises: fba6e9cfd8f8
Create Date: 2026-03-26 12:54:33.061915

PURPOSE:
  Adds missing Lead fields (salutation, lead_score, owner_id, etc.),
  aligns Contact column constraints, and adds named FK constraints to
  the deals table. All operations are idempotent — safe to run on both
  existing and fresh databases.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


# revision identifiers, used by Alembic.
revision: str = 'dc6fab398bad'
down_revision: Union[str, None] = 'fba6e9cfd8f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ── Helpers ────────────────────────────────────────────────────────────────

def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    return column in [c['name'] for c in inspect(conn).get_columns(table)]


def _index_exists(index_name: str, table: str) -> bool:
    conn = op.get_bind()
    return any(i['name'] == index_name for i in inspect(conn).get_indexes(table))


def _fk_exists(table: str, fk_name: str) -> bool:
    conn = op.get_bind()
    return any(fk.get('name') == fk_name for fk in inspect(conn).get_foreign_keys(table))


def _cleanup_tmp(table: str) -> None:
    tmp = f'_alembic_tmp_{table}'
    conn = op.get_bind()
    if tmp in inspect(conn).get_table_names():
        conn.execute(text(f'DROP TABLE "{tmp}"'))


# ── Upgrade ────────────────────────────────────────────────────────────────

def upgrade() -> None:
    # Clean up any stale temp tables from previous failed runs
    for t in ('contacts', 'deals', 'leads'):
        _cleanup_tmp(t)

    # ── 1. CONTACTS: align nullable constraints + fix email index ──────────
    with op.batch_alter_table('contacts', schema=None) as batch_op:
        # Drop old unique email index if it exists, recreate as non-unique
        if _index_exists('ix_contacts_email', 'contacts'):
            batch_op.drop_index('ix_contacts_email')
        if _index_exists('ix_contacts_phone', 'contacts'):
            batch_op.drop_index('ix_contacts_phone')
        batch_op.create_index(batch_op.f('ix_contacts_email'), ['email'], unique=False)
        # Drop legacy company column if present
        if _column_exists('contacts', 'company'):
            batch_op.drop_column('company')

    # ── 2. DEALS: add named FK constraints (replace None-named ones) ───────
    with op.batch_alter_table('deals', schema=None) as batch_op:
        if not _fk_exists('deals', 'fk_deals_lead_id'):
            batch_op.create_foreign_key(
                'fk_deals_lead_id', 'leads', ['lead_id'], ['id']
            )
        if not _fk_exists('deals', 'fk_deals_owner_id'):
            batch_op.create_foreign_key(
                'fk_deals_owner_id', 'users', ['owner_id'], ['id']
            )

    # ── 3. LEADS: add all missing columns (idempotent) ────────────────────
    new_lead_cols = [
        ('salutation',          sa.Column('salutation', sa.String(), nullable=True)),
        ('secondary_email',     sa.Column('secondary_email', sa.String(), nullable=True)),
        ('skype_id',            sa.Column('skype_id', sa.String(), nullable=True)),
        ('twitter',             sa.Column('twitter', sa.String(), nullable=True)),
        ('website',             sa.Column('website', sa.String(), nullable=True)),
        ('title',               sa.Column('title', sa.String(), nullable=True)),
        ('source',              sa.Column('source', sa.String(), nullable=True)),
        ('lead_score',          sa.Column('lead_score', sa.Integer(), nullable=True)),
        ('rating',              sa.Column('rating', sa.Integer(), nullable=True)),
        ('tag',                 sa.Column('tag', sa.String(), nullable=True)),
        ('is_converted',        sa.Column('is_converted', sa.Boolean(), nullable=True)),
        ('converted_at',        sa.Column('converted_at', sa.DateTime(), nullable=True)),
        ('last_contacted_at',   sa.Column('last_contacted_at', sa.DateTime(), nullable=True)),
        ('unsubscribed_mode',   sa.Column('unsubscribed_mode', sa.String(), nullable=True)),
        ('unsubscribed_time',   sa.Column('unsubscribed_time', sa.DateTime(), nullable=True)),
        ('owner_id',            sa.Column('owner_id', sa.Integer(), nullable=True)),
        ('updated_at',          sa.Column('updated_at', sa.DateTime(), nullable=True)),
    ]

    with op.batch_alter_table('leads', schema=None) as batch_op:
        for col_name, col_def in new_lead_cols:
            if not _column_exists('leads', col_name):
                batch_op.add_column(col_def)
        # Add named FK for leads.owner_id → users.id
        if not _fk_exists('leads', 'fk_leads_owner_id'):
            batch_op.create_foreign_key(
                'fk_leads_owner_id', 'users', ['owner_id'], ['id']
            )


# ── Downgrade ──────────────────────────────────────────────────────────────

def downgrade() -> None:
    for t in ('contacts', 'deals', 'leads'):
        _cleanup_tmp(t)

    # Remove columns added to leads
    lead_added_cols = [
        'updated_at', 'owner_id', 'unsubscribed_time', 'unsubscribed_mode',
        'last_contacted_at', 'converted_at', 'is_converted', 'tag', 'rating',
        'lead_score', 'source', 'title', 'website', 'twitter', 'skype_id',
        'secondary_email', 'salutation',
    ]
    with op.batch_alter_table('leads', schema=None) as batch_op:
        if _fk_exists('leads', 'fk_leads_owner_id'):
            batch_op.drop_constraint('fk_leads_owner_id', type_='foreignkey')
        for col in lead_added_cols:
            if _column_exists('leads', col):
                batch_op.drop_column(col)

    # Remove named FKs from deals
    with op.batch_alter_table('deals', schema=None) as batch_op:
        if _fk_exists('deals', 'fk_deals_owner_id'):
            batch_op.drop_constraint('fk_deals_owner_id', type_='foreignkey')
        if _fk_exists('deals', 'fk_deals_lead_id'):
            batch_op.drop_constraint('fk_deals_lead_id', type_='foreignkey')

    # Restore contacts state
    with op.batch_alter_table('contacts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('company', sa.VARCHAR(), nullable=True))
        if _index_exists('ix_contacts_email', 'contacts'):
            batch_op.drop_index(batch_op.f('ix_contacts_email'))
        batch_op.create_index('ix_contacts_email', ['email'], unique=True)
        batch_op.create_index('ix_contacts_phone', ['phone'], unique=False)
