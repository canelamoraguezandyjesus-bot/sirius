"""robot 0.2: los bits de cada huella, para buscar en dos pasos

Revision ID: 43d72bb058bd
Revises: b0f472943480
Create Date: 2026-10-17 01:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '43d72bb058bd'
down_revision: str | Sequence[str] | None = 'b0f472943480'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # ADR-251: de cada huella, un bit por número, 1 si es positivo. Con muchas huellas,
    # la búsqueda mira primero los bits de todas y el coseno exacto solo de las más
    # cercanas. Las huellas de antes se quedan sin bits y la búsqueda va en un solo paso
    # hasta que se recalculen. El índice lleva el modelo y los bits para que el primer
    # paso los lea sin abrir cada huella.
    op.add_column('memory_embeddings', sa.Column('bits', sa.LargeBinary(), nullable=True))
    op.create_index(
        'ix_memory_embeddings_model_bits', 'memory_embeddings', ['model', 'bits']
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_memory_embeddings_model_bits', table_name='memory_embeddings')
    # Sin rehacer la tabla: los disparadores de `memories` y `memory_revisions` la nombran,
    # y SQLite no deja renombrar una copia mientras la nombran.
    op.execute('ALTER TABLE memory_embeddings DROP COLUMN bits')
