"""robot 0.2: las notas del juez

Revision ID: 5ae46b266506
Revises: 7a3e9c2d4b10
Create Date: 2026-10-07 16:40:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '5ae46b266506'
down_revision: str | Sequence[str] | None = '7a3e9c2d4b10'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Pieza E de ADR-233: la nota del 1 al 5 que el juez da a cada respuesta de
    # Sirius y si con ella avisó de que baja (PA-R02-08). Solo números: el texto
    # de la respuesta sigue estando solo en `messages`.
    op.create_table(
        'judge_scores',
        sa.Column('message_id', sa.Integer(), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False),
        sa.Column('warned', sa.Boolean(), nullable=False),
        sa.Column('judged_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('message_id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('judge_scores')
