"""robot 0.2: modos, marcas y resúmenes de la charla

Revision ID: 7a3e9c2d4b10
Revises: de3545536503
Create Date: 2026-10-07 16:20:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '7a3e9c2d4b10'
down_revision: str | Sequence[str] | None = 'de3545536503'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Pieza D de ADR-233: tres tablas nuevas y ninguna columna nueva en las de
    # siempre. «Ponte serio» y «para» (PA-R02-04), las marcas «eso es Sirius» /
    # «eso no» con el modelo de cada respuesta (PA-R02-06) y el resumen de la
    # charla larga (PA-R02-05).
    op.create_table(
        'conversation_modes',
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('mode', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('conversation_id'),
    )
    op.create_table(
        'reply_marks',
        sa.Column('message_id', sa.Integer(), nullable=False),
        sa.Column('model', sa.Text(), nullable=True),
        sa.Column('mark', sa.Text(), nullable=True),
        sa.Column('marked_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('message_id'),
    )
    op.create_table(
        'conversation_summaries',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('up_to_sequence', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('conversation_summaries')
    op.drop_table('reply_marks')
    op.drop_table('conversation_modes')
