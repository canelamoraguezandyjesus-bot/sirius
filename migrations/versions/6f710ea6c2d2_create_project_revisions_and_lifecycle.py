"""create project revisions and lifecycle

Revision ID: 6f710ea6c2d2
Revises: 66951344e4b9
Create Date: 2026-07-17 23:58:19.916299

"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '6f710ea6c2d2'
down_revision: str | Sequence[str] | None = '66951344e4b9'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### create project_revisions: immutable, versioned continuity history.
    # Which revision is "current" is decided exclusively by
    # projects.current_revision_id (added below) pointing at a row's id —
    # this table carries no is_current flag or other second source of
    # truth (SIRIUS-ARQ-0.1 S7.3 "Campos mínimos": project_revision has no
    # is_current field either). ###
    op.create_table(
        'project_revisions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('objective', sa.Text(), nullable=False),
        sa.Column('state_summary', sa.Text(), nullable=False),
        sa.Column('blockers_json', sa.Text(), nullable=False),
        sa.Column('next_step', sa.Text(), nullable=False),
        sa.Column('source_event_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'version', name='uq_project_revisions_project_version'),
    )

    # ### add structural lifecycle columns to projects (legacy flat columns
    # are kept for non-destructive compatibility; see ProjectModel docstring).
    # current_revision_id is the architecture's authoritative minimum field
    # (SIRIUS-ARQ-0.1 S7.3) for "which revision is current" — NULL only for
    # the neutral bootstrap placeholder, which has no revision yet.
    #
    # A physical FK (current_revision_id -> project_revisions.id) is used
    # rather than an application-only pointer: empirically verified against
    # this project's SQLite version that ALTER TABLE ADD COLUMN with a
    # REFERENCES clause, and later dropping that column, both work directly
    # (no batch/table-rebuild required — PRAGMA foreign_keys=ON is already
    # enabled on every connection, see database.py), so there is no
    # "reconstrucción arriesgada" to avoid here. This FK only guarantees the
    # referenced row exists, not that it belongs to the same project; the
    # repository additionally validates that at read time and rejects a
    # cross-project reference as data corruption. ###
    op.add_column(
        'projects',
        sa.Column(
            'status',
            sa.Enum(
                'active', 'completed',
                name='projectstatus', native_enum=False, length=16,
            ),
            nullable=False,
            server_default='active',
        ),
    )
    op.add_column('projects', sa.Column('completed_at', sa.DateTime(), nullable=True))
    # Issued as raw DDL rather than op.add_column(sa.Column(..., ForeignKey(...))):
    # Alembic's SQLite dialect implements a column-level FK added via
    # op.add_column as two operations (add the column, then a separate
    # ADD CONSTRAINT), and the second one is unsupported for SQLite outside
    # batch mode ("No support for ALTER of constraints in SQLite dialect"),
    # which would force the risky copy-and-move table reconstruction this
    # migration deliberately avoids. A single ALTER TABLE ... ADD COLUMN ...
    # REFERENCES statement, by contrast, is understood and enforced natively
    # by SQLite itself (empirically verified: PRAGMA foreign_key_check finds
    # no issues, and it correctly rejects a nonexistent revision id) — no
    # rebuild needed either way.
    op.execute(
        'ALTER TABLE projects ADD COLUMN current_revision_id INTEGER '
        'REFERENCES project_revisions (id)'
    )

    # ### backfill: classify every existing row, seed its revision 1, and
    # point current_revision_id at it ###
    connection = op.get_bind()
    projects = sa.table(
        'projects',
        sa.column('id', sa.Integer()),
        sa.column('name', sa.Text()),
        sa.column('objective', sa.Text()),
        sa.column('current_state', sa.Text()),
        sa.column('blockers', sa.Text()),
        sa.column('next_step', sa.Text()),
        sa.column('is_active', sa.Boolean()),
        sa.column('status', sa.Text()),
        sa.column('completed_at', sa.DateTime()),
        sa.column('current_revision_id', sa.Integer()),
        sa.column('created_at', sa.DateTime()),
        sa.column('updated_at', sa.DateTime()),
    )
    project_revisions = sa.table(
        'project_revisions',
        sa.column('id', sa.Integer()),
        sa.column('project_id', sa.Integer()),
        sa.column('version', sa.Integer()),
        sa.column('objective', sa.Text()),
        sa.column('state_summary', sa.Text()),
        sa.column('blockers_json', sa.Text()),
        sa.column('next_step', sa.Text()),
        sa.column('source_event_id', sa.Integer()),
        sa.column('created_at', sa.DateTime()),
    )

    existing_rows = connection.execute(
        sa.select(
            projects.c.id,
            projects.c.name,
            projects.c.objective,
            projects.c.current_state,
            projects.c.blockers,
            projects.c.next_step,
            projects.c.is_active,
            projects.c.created_at,
            projects.c.updated_at,
        )
    ).fetchall()

    for row in existing_rows:
        # A row counts as "configured" using the exact B3b rule: non-empty
        # name and objective. An inactive (is_active=false) row — not
        # expected in practice before this migration, since no prior code
        # path ever produced one, but handled generally and tested — is
        # migrated as COMPLETED, using its own updated_at as the migration's
        # best-effort completed_at (documented, conservative choice: no
        # other timestamp is available).
        is_row_configured = bool((row.name or '').strip()) and bool((row.objective or '').strip())
        new_status = 'active' if row.is_active else 'completed'
        new_completed_at = None if row.is_active else row.updated_at

        connection.execute(
            projects.update()
            .where(projects.c.id == row.id)
            .values(status=new_status, completed_at=new_completed_at)
        )

        if is_row_configured:
            blockers_text = row.blockers or ''
            blocker_lines = [line.strip() for line in blockers_text.splitlines() if line.strip()]
            result = connection.execute(
                project_revisions.insert().values(
                    project_id=row.id,
                    version=1,
                    objective=row.objective,
                    state_summary=row.current_state or '',
                    blockers_json=json.dumps(blocker_lines),
                    next_step=row.next_step or '',
                    source_event_id=None,
                    # Conservative choice: updated_at reflects the most
                    # recent known change to this content, which is exactly
                    # what a revision's created_at should represent for a
                    # row migrated from the pre-revision (B3b) schema.
                    created_at=row.updated_at,
                )
            )
            # sa.table() is a lightweight TableClause with no declared
            # primary key, so SQLAlchemy cannot populate
            # inserted_primary_key here; lastrowid is what SQLite's own
            # driver reports for the row this single INSERT just created.
            new_revision_id = result.lastrowid
            connection.execute(
                projects.update()
                .where(projects.c.id == row.id)
                .values(current_revision_id=new_revision_id)
            )
        # An unconfigured placeholder gets no revision row: current_revision_id
        # stays NULL, matching a brand-new placeholder.


def downgrade() -> None:
    """Downgrade schema."""
    connection = op.get_bind()
    projects = sa.table(
        'projects',
        sa.column('id', sa.Integer()),
        sa.column('objective', sa.Text()),
        sa.column('current_state', sa.Text()),
        sa.column('blockers', sa.Text()),
        sa.column('next_step', sa.Text()),
        sa.column('current_revision_id', sa.Integer()),
    )
    project_revisions = sa.table(
        'project_revisions',
        sa.column('id', sa.Integer()),
        sa.column('objective', sa.Text()),
        sa.column('state_summary', sa.Text()),
        sa.column('blockers_json', sa.Text()),
        sa.column('next_step', sa.Text()),
    )

    # Sync the legacy flat columns from each project's current revision
    # (found via current_revision_id) before the revision table is dropped,
    # so the downgraded (B3b-shaped) database still reflects the latest
    # known continuity content. The revision history itself is unavoidably
    # lost below: the B3b schema this downgrade restores has no columns
    # capable of representing more than one snapshot per project. This is
    # the documented, expected consequence of downgrading past a schema
    # that added real historical versioning — not a silent failure.
    current_projects = connection.execute(
        sa.select(projects.c.id, projects.c.current_revision_id).where(
            projects.c.current_revision_id.is_not(None)
        )
    ).fetchall()

    for project_row in current_projects:
        revision_row = connection.execute(
            sa.select(
                project_revisions.c.objective,
                project_revisions.c.state_summary,
                project_revisions.c.blockers_json,
                project_revisions.c.next_step,
            ).where(project_revisions.c.id == project_row.current_revision_id)
        ).one()
        blocker_lines = json.loads(revision_row.blockers_json)
        connection.execute(
            projects.update()
            .where(projects.c.id == project_row.id)
            .values(
                objective=revision_row.objective,
                current_state=revision_row.state_summary,
                blockers='\n'.join(blocker_lines),
                next_step=revision_row.next_step,
            )
        )

    # current_revision_id is dropped before project_revisions itself, since
    # it holds a foreign key into that table.
    op.drop_column('projects', 'current_revision_id')
    op.drop_table('project_revisions')
    op.drop_column('projects', 'completed_at')
    op.drop_column('projects', 'status')
