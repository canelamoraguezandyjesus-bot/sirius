"""robot 0.2: las huellas de los recuerdos

Revision ID: eebe9128da2c
Revises: 5ae46b266506
Create Date: 2026-10-07 18:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'eebe9128da2c'
down_revision: str | Sequence[str] | None = '5ae46b266506'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Pieza F de ADR-233 (ADR-238): la huella de cada recuerdo, de su revisión
    # actual y con el modelo que la dio, en la misma base. Una tabla normal con
    # la huella en un BLOB: la busca la función vec_distance_cosine de
    # sqlite-vec, así que esta migración no necesita cargar la extensión.
    op.create_table(
        'memory_embeddings',
        sa.Column('memory_id', sa.Integer(), nullable=False),
        sa.Column('revision_id', sa.Integer(), nullable=False),
        sa.Column('model', sa.Text(), nullable=False),
        sa.Column('embedding', sa.LargeBinary(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['memory_id'], ['memories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['revision_id'], ['memory_revisions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('memory_id'),
    )
    # Un recuerdo borrado o archivado se lleva su huella. Una huella deja
    # adivinar algo de lo que decía: borrar un recuerdo tiene que borrarla
    # también, lo borre quien lo borre. Si un recuerdo volviera a estar vigente,
    # la ventana calcularía otra.
    op.execute(
        """
        CREATE TRIGGER memory_embeddings_fuera_si_deja_de_estar_vigente
        AFTER UPDATE OF status ON memories WHEN new.status != 'current' BEGIN
            DELETE FROM memory_embeddings WHERE memory_id = new.id;
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER memory_embeddings_fuera_si_se_borra_el_contenido
        AFTER UPDATE OF content ON memory_revisions WHEN new.content IS NULL BEGIN
            DELETE FROM memory_embeddings WHERE memory_id = new.memory_id;
        END
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TRIGGER IF EXISTS memory_embeddings_fuera_si_se_borra_el_contenido")
    op.execute("DROP TRIGGER IF EXISTS memory_embeddings_fuera_si_deja_de_estar_vigente")
    op.drop_table('memory_embeddings')
