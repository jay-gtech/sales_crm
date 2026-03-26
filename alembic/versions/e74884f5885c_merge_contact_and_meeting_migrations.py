"""merge contact and meeting migrations

Revision ID: e74884f5885c
Revises: 60de3461f98f, b1c2d3e4f5a6
Create Date: 2026-03-25 17:45:59.411598

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e74884f5885c'
down_revision: Union[str, None] = ('60de3461f98f', 'b1c2d3e4f5a6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
