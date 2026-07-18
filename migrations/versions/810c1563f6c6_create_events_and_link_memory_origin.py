"""create events and link memory origin

Revision ID: 810c1563f6c6
Revises: 6f710ea6c2d2
Create Date: 2026-07-18 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '810c1563f6c6'
down_revision: str | Sequence[str] | None = '6f710ea6c2d2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### create events: minimal persistent representation of "el evento de
    # origen" (SIRIUS-ARQ-0.1 S7.1/S7.3), non-destructive and additive only.
    # B4a populates event_type/actor/message_id/created_at; redacted_at stays
    # NULL until B4d adds redaction. ###
    op.create_table(
        'events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('event_type', sa.Text(), nullable=False),
        sa.Column('actor', sa.Text(), nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('redacted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )

    # ### link memory_revisions to its origin event (B4a, RF-021). A single
    # ALTER TABLE ... ADD COLUMN ... REFERENCES statement is used rather than
    # op.add_column(sa.Column(..., ForeignKey(...))) for the same reason as
    # 6f710ea6c2d2: SQLite understands and enforces it natively (PRAGMA
    # foreign_keys=ON is already set on every connection), avoiding the
    # unsupported two-step "ADD CONSTRAINT" Alembic would otherwise emit for
    # SQLite outside batch mode. Every existing memory_revisions row gets
    # source_event_id = NULL — correct, since no event existed before this
    # migration; no backfill is possible or needed. ###
    op.execute(
        'ALTER TABLE memory_revisions ADD COLUMN source_event_id INTEGER '
        'REFERENCES events (id)'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('memory_revisions', 'source_event_id')
    op.drop_table('events')
