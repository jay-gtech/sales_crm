"""Add extended fields to contacts table

Revision ID: b1c2d3e4f5a6
Revises: a457a9f724e2
Create Date: 2026-03-25 15:42:00.000000

This migration is purely ADDITIVE — it only adds new nullable columns to the
existing `contacts` table. No existing columns are modified or removed.
Dependencies: deals → contacts.id and activities → contacts.id remain intact.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, None] = 'a457a9f724e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ── Columns to add (all nullable, safe for existing rows) ────────────────────
NEW_COLUMNS = [
    # name,               sa_type,           extras
    ("salutation",        sa.String(),        {}),
    ("contact_owner",     sa.String(),        {}),
    ("lead_source",       sa.String(),        {}),
    ("account_name",      sa.String(),        {}),
    ("vendor_name",       sa.String(),        {}),
    ("secondary_email",   sa.String(),        {}),
    ("title",             sa.String(),        {}),
    ("department",        sa.String(),        {}),
    ("other_phone",       sa.String(),        {}),
    ("home_phone",        sa.String(),        {}),
    ("mobile",            sa.String(),        {}),
    ("fax",               sa.String(),        {}),
    ("assistant",         sa.String(),        {}),
    ("asst_phone",        sa.String(),        {}),
    ("date_of_birth",     sa.Date(),          {}),
    ("email_opt_out",     sa.Boolean(),       {"server_default": "0"}),
    ("skype_id",          sa.String(),        {}),
    ("twitter",           sa.String(),        {}),
    ("reporting_to",      sa.String(),        {}),
    ("mailing_building",  sa.String(),        {}),
    ("mailing_street",    sa.String(),        {}),
    ("mailing_city",      sa.String(),        {}),
    ("mailing_state",     sa.String(),        {}),
    ("mailing_zip",       sa.String(),        {}),
    ("mailing_country",   sa.String(),        {}),
    ("mailing_lat",       sa.String(),        {}),
    ("mailing_lng",       sa.String(),        {}),
    ("other_building",    sa.String(),        {}),
    ("other_street",      sa.String(),        {}),
    ("other_city",        sa.String(),        {}),
    ("other_state",       sa.String(),        {}),
    ("other_zip",         sa.String(),        {}),
    ("other_country",     sa.String(),        {}),
    ("other_lat",         sa.String(),        {}),
    ("other_lng",         sa.String(),        {}),
    ("description",       sa.String(),        {}),
    ("contact_image",     sa.String(),        {}),
    ("created_at",        sa.DateTime(),      {}),
]

# Columns that the INITIAL migration already created — skip adding them again.
_ALREADY_EXISTS = {
    "id", "first_name", "last_name", "email", "phone",
    "company",           # created by initial migration (not in new model but won't break)
    "lead_id",           # FK created by initial migration
    "created_at",        # created by initial migration
}


def upgrade() -> None:
    # Use batch_alter_table for SQLite compatibility (SQLite doesn't support
    # ALTER TABLE ADD COLUMN ... with constraints in all contexts, but the
    # batch mode handles it transparently).
    with op.batch_alter_table("contacts", schema=None) as batch_op:
        for col_name, col_type, extras in NEW_COLUMNS:
            if col_name in _ALREADY_EXISTS:
                continue
            batch_op.add_column(
                sa.Column(col_name, col_type, nullable=True, **extras)
            )


def downgrade() -> None:
    with op.batch_alter_table("contacts", schema=None) as batch_op:
        for col_name, _col_type, _extras in reversed(NEW_COLUMNS):
            if col_name in _ALREADY_EXISTS:
                continue
            batch_op.drop_column(col_name)
