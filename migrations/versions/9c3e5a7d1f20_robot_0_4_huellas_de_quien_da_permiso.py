"""robot 0.4: las huellas cifradas de quien da permiso para que le reconozca

Revision ID: 9c3e5a7d1f20
Revises: 43d72bb058bd
Create Date: 2026-10-19 03:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9c3e5a7d1f20'
down_revision: str | Sequence[str] | None = '43d72bb058bd'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # ADR-263: de quien da permiso, la huella de su cara y la de su voz, cifradas. La llave
    # vive en el almacén de secretos, nunca aquí.
    op.create_table(
        'recognition_prints',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('person', sa.Text(), nullable=False),
        sa.Column('kind', sa.Text(), nullable=False),
        sa.Column('sealed', sa.LargeBinary(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_recognition_prints_person', 'recognition_prints', ['person'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_recognition_prints_person', table_name='recognition_prints')
    op.drop_table('recognition_prints')
