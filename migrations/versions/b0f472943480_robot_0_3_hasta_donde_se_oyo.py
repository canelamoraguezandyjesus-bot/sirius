"""robot 0.3: hasta dónde se oyó una respuesta de Sirius que le cortaron

Revision ID: b0f472943480
Revises: 96dcb8c3d40e
Create Date: 2026-10-15 23:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b0f472943480'
down_revision: str | Sequence[str] | None = '96dcb8c3d40e'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # ADR-245: si le cortan mientras dice una respuesta, la respuesta se guarda entera y
    # además se apunta lo que el propietario llegó a oír, para que el modelo no dé por
    # dicho lo que no sonó. Los mensajes de antes se quedan como estaban, sin corte.
    op.add_column('messages', sa.Column('heard_when_cut', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('messages') as batch_op:
        batch_op.drop_column('heard_when_cut')
