"""add message operation_id and identity_version

Revision ID: f5fb28ed426a
Revises: bd39e7e3df5e
Create Date: 2026-07-12 17:28:47.985084

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f5fb28ed426a'
down_revision: str | Sequence[str] | None = 'bd39e7e3df5e'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('messages', sa.Column('operation_id', sa.Text(), nullable=True))
    op.add_column('messages', sa.Column('identity_version', sa.Integer(), nullable=True))
    op.add_column(
        'messages',
        sa.Column(
            'status',
            sa.Enum(
                'completed', 'cancelled', 'failed',
                name='messagestatus', native_enum=False, length=16,
            ),
            nullable=False,
            server_default='completed',
        ),
    )
    # SQLite cannot ADD CONSTRAINT directly; batch mode recreates the table.
    with op.batch_alter_table('messages') as batch_op:
        batch_op.create_unique_constraint(
            'uq_messages_operation_role', ['conversation_id', 'operation_id', 'role']
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('messages') as batch_op:
        batch_op.drop_constraint('uq_messages_operation_role', type_='unique')
    op.drop_column('messages', 'status')
    op.drop_column('messages', 'identity_version')
    op.drop_column('messages', 'operation_id')
