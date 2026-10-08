"""robot 0.2: los hechos con su fecha y quién lo dijo, y los resúmenes del día

Revision ID: 2c3461a7e6a7
Revises: eebe9128da2c
Create Date: 2026-10-07 22:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '2c3461a7e6a7'
down_revision: str | Sequence[str] | None = 'eebe9128da2c'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Pieza G de ADR-233 (ADR-239). Un hecho es un recuerdo con persona y tema;
    # cada revisión suya es un tramo, con desde cuándo vale, hasta cuándo, quién
    # lo dijo y con qué seguridad. Todo admite NULL: los recuerdos de siempre no
    # son hechos y siguen igual.
    op.add_column('memories', sa.Column('person', sa.Text(), nullable=True))
    op.add_column('memories', sa.Column('topic', sa.Text(), nullable=True))
    op.add_column('memory_revisions', sa.Column('valid_from', sa.Date(), nullable=True))
    op.add_column('memory_revisions', sa.Column('valid_to', sa.Date(), nullable=True))
    op.add_column('memory_revisions', sa.Column('said_by', sa.Text(), nullable=True))
    op.add_column('memory_revisions', sa.Column('certainty', sa.Text(), nullable=True))

    # Lo que propone el sueño es un hecho de alguien, y «eso no es así» propone
    # corregir uno: las dos esperan su sí como cualquier sugerencia.
    op.add_column('memory_suggestions', sa.Column('person', sa.Text(), nullable=True))
    op.add_column('memory_suggestions', sa.Column('topic', sa.Text(), nullable=True))
    op.add_column('memory_suggestions', sa.Column('valid_from', sa.Date(), nullable=True))
    op.add_column('memory_suggestions', sa.Column('said_by', sa.Text(), nullable=True))
    op.add_column('memory_suggestions', sa.Column('certainty', sa.Text(), nullable=True))
    # Como DDL a mano, igual que current_revision_id en 6f710ea6c2d2: Alembic no
    # sabe añadir en SQLite una columna con su clave ajena sin rehacer la tabla.
    op.execute(
        'ALTER TABLE memory_suggestions ADD COLUMN corrects_memory_id INTEGER '
        'REFERENCES memories (id)'
    )

    # El resumen de cada día que sueña: uno por día.
    op.create_table(
        'day_summaries',
        sa.Column('day', sa.Date(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('day'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('day_summaries')
    # memory_suggestions no tiene disparadores: se puede rehacer, y hace falta
    # para quitar una columna con clave ajena.
    with op.batch_alter_table('memory_suggestions') as batch_op:
        batch_op.drop_column('corrects_memory_id')
        batch_op.drop_column('certainty')
        batch_op.drop_column('said_by')
        batch_op.drop_column('valid_from')
        batch_op.drop_column('topic')
        batch_op.drop_column('person')
    # Estas dos sí los tienen, los de la búsqueda por palabras y los de las
    # huellas: se quitan las columnas sin rehacer la tabla, que los perdería.
    for column in ('certainty', 'said_by', 'valid_to', 'valid_from'):
        op.drop_column('memory_revisions', column)
    for column in ('topic', 'person'):
        op.drop_column('memories', column)
