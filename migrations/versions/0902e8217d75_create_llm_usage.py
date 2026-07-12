"""create llm usage

Revision ID: 0902e8217d75
Revises: f5fb28ed426a
Create Date: 2026-07-12 18:05:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '0902e8217d75'
down_revision: str | Sequence[str] | None = 'f5fb28ed426a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'llm_usage',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('year_month', sa.Text(), nullable=False),
        sa.Column('spent_usd', sa.Float(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('year_month'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('llm_usage')
