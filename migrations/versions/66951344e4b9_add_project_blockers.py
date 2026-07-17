"""add project blockers

Revision ID: 66951344e4b9
Revises: 0902e8217d75
Create Date: 2026-07-17 20:46:08.944659

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '66951344e4b9'
down_revision: str | Sequence[str] | None = '0902e8217d75'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'projects', sa.Column('blockers', sa.Text(), nullable=False, server_default='')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('projects', 'blockers')
