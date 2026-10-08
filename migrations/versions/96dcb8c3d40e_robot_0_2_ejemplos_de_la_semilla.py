"""robot 0.2: los ejemplos de la semilla, guardados aparte en cada versión de la identidad

Revision ID: 96dcb8c3d40e
Revises: 2c3461a7e6a7
Create Date: 2026-10-08 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '96dcb8c3d40e'
down_revision: str | Sequence[str] | None = '2c3461a7e6a7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # ADR-240: los ejemplos de charla de cada versión de la identidad, en JSON, para
    # que la charla le enseñe en cada turno los que más se parecen a lo que se habla
    # y no todos en fila. Las versiones de antes se quedan como estaban, con «[]»:
    # las de la semilla del robot los llevan dentro del texto.
    op.add_column(
        'identity_versions',
        sa.Column('examples', sa.Text(), nullable=False, server_default='[]'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('identity_versions', 'examples')
