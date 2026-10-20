"""robot 0.4: lo que recuerda haber visto, como texto

Revision ID: b5f1c8e2a4d7
Revises: 9c3e5a7d1f20
Create Date: 2026-10-19 05:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b5f1c8e2a4d7'
down_revision: str | Sequence[str] | None = '9c3e5a7d1f20'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # ADR-265: cuándo cambió quién tenía delante, qué cambió y quién, su nombre si dio
    # permiso o nada. Ninguna imagen.
    op.create_table(
        'sight_log',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('seen_at', sa.DateTime(), nullable=False),
        sa.Column('change', sa.Text(), nullable=False),
        sa.Column('person', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_sight_log_seen_at', 'sight_log', ['seen_at'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_sight_log_seen_at', table_name='sight_log')
    op.drop_table('sight_log')
