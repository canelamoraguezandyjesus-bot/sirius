"""create fts5 search indexes

Revision ID: 61be4bb269bf
Revises: 94418c79da9d
Create Date: 2026-07-21 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '61be4bb269bf'
down_revision: str | Sequence[str] | None = '94418c79da9d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema.

    B6a (SIRIUS-ARQ-0.1 S7.1/S8.1; ATD-004; D-11): the local search
    substrate. Two FTS5 virtual tables, populated by triggers so every write
    to the data they index and the corresponding index update happen inside
    the exact same transaction (S8.1) — no application code has to remember
    to keep them in sync, and a rollback of the data automatically rolls
    back the index update with it. Hand-written (``op.execute``): FTS5
    tables and triggers have no SQLAlchemy/Alembic autogeneration support.

    ``message_fts`` is an "external content" FTS5 table over ``messages``
    (``content_rowid='id'``): it stores no copy of the text, only the
    tokenized index, and reads ``content`` live from ``messages`` on every
    query — so a message row is the single source of truth for its own
    text, exactly once. Triggers cover every write path: ``INSERT``
    (``SendMessageUseCase``), ``UPDATE`` (``ConversationRepository
    .redact_message``, B4d — content becomes NULL), and ``DELETE`` (no
    repository method deletes a message today, but ``messages.conversation_id``
    has ``ondelete='CASCADE'`` on ``conversations``, so covering it keeps the
    invariant structural rather than dependent on today's call graph).

    ``knowledge_fts`` covers both memories and decisions — the same
    "conocimiento" grouping B4f's ``GetKnowledgeOverviewUseCase`` already
    uses — since neither table alone is "the knowledge a user asked
    Sirius to remember or decide". It is a self-contained (non-external
    content) FTS5 table: unlike messages, a memory/decision's text lives
    across several revision rows (only one ``is_current``), so there is no
    single source row FTS5's external-content mode could point at; instead
    each trigger writes the *current* revision's content as one row keyed by
    a synthetic rowid that keeps the two id spaces apart without a shared
    sequence: ``memory_id * 2`` (even) for memories, ``decision_id * 2 + 1``
    (odd) for decisions. Every write is delete-then-insert, the standard
    FTS5 idiom for keeping a trigger-synced table consistent on both insert
    and update.

    Sync coverage per source table:

    - ``memory_revisions`` ``INSERT ... WHEN new.is_current`` covers a new
      memory (``SaveManualMemoryUseCase``) and a correction's new revision
      (``CorrectMemoryUseCase`` — the old revision's ``is_current`` flips to
      0 first, then the new current revision is inserted, so the trigger
      always ends up reflecting the vigente text).
    - ``memory_revisions`` ``UPDATE OF content ... WHEN new.is_current``
      covers ``DeleteMemoryUseCase``: ``MemoryRepository.delete_memory``
      nulls ``content`` on every revision of a memory, including the
      current one, without touching ``is_current`` — this is the trigger
      that must fire for the deleted memory's text to stop matching any
      query. ``DELETE`` also covers the CASCADE that would follow a memory
      row itself being removed, for the same structural reason as messages.
    - ``decision_revisions`` ``INSERT ... WHEN new.is_current`` covers a
      proposed decision (``ProposeDecisionUseCase``): decisions never gain
      a second revision (substitution creates a new ``Decision`` row
      instead, see ``sirius.domain.decision``), so no ``UPDATE`` trigger is
      needed — a decision's content, once inserted, never changes.
      Archiving/approving/superseding only ever change ``decisions.status``,
      never ``decision_revisions.content``, so they need no trigger of
      their own to keep ``knowledge_fts`` faithful to the vigente text.

    Both tables are backfilled from whatever the previous head already
    contains, so upgrading an existing database does not lose search
    coverage over data written before this migration.
    """
    op.execute(
        "CREATE VIRTUAL TABLE message_fts USING fts5("
        "content, content='messages', content_rowid='id')"
    )
    op.execute(
        """
        CREATE TRIGGER messages_fts_ai AFTER INSERT ON messages BEGIN
            INSERT INTO message_fts(rowid, content) VALUES (new.id, new.content);
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER messages_fts_ad AFTER DELETE ON messages BEGIN
            INSERT INTO message_fts(message_fts, rowid, content)
                VALUES('delete', old.id, old.content);
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER messages_fts_au AFTER UPDATE ON messages BEGIN
            INSERT INTO message_fts(message_fts, rowid, content)
                VALUES('delete', old.id, old.content);
            INSERT INTO message_fts(rowid, content) VALUES (new.id, new.content);
        END
        """
    )
    op.execute(
        "INSERT INTO message_fts(rowid, content) SELECT id, content FROM messages"
    )

    op.execute(
        "CREATE VIRTUAL TABLE knowledge_fts USING fts5(kind UNINDEXED, item_id UNINDEXED, content)"
    )
    op.execute(
        """
        CREATE TRIGGER memory_revisions_fts_ai AFTER INSERT ON memory_revisions
        WHEN new.is_current = 1 BEGIN
            DELETE FROM knowledge_fts WHERE rowid = new.memory_id * 2;
            INSERT INTO knowledge_fts(rowid, kind, item_id, content)
                SELECT new.memory_id * 2, 'memory', new.memory_id, new.content
                WHERE new.content IS NOT NULL;
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER memory_revisions_fts_au AFTER UPDATE OF content ON memory_revisions
        WHEN new.is_current = 1 BEGIN
            DELETE FROM knowledge_fts WHERE rowid = new.memory_id * 2;
            INSERT INTO knowledge_fts(rowid, kind, item_id, content)
                SELECT new.memory_id * 2, 'memory', new.memory_id, new.content
                WHERE new.content IS NOT NULL;
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER memory_revisions_fts_ad AFTER DELETE ON memory_revisions
        WHEN old.is_current = 1 BEGIN
            DELETE FROM knowledge_fts WHERE rowid = old.memory_id * 2;
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER decision_revisions_fts_ai AFTER INSERT ON decision_revisions
        WHEN new.is_current = 1 BEGIN
            DELETE FROM knowledge_fts WHERE rowid = new.decision_id * 2 + 1;
            INSERT INTO knowledge_fts(rowid, kind, item_id, content)
                SELECT new.decision_id * 2 + 1, 'decision', new.decision_id, new.content
                WHERE new.content IS NOT NULL;
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER decision_revisions_fts_ad AFTER DELETE ON decision_revisions
        WHEN old.is_current = 1 BEGIN
            DELETE FROM knowledge_fts WHERE rowid = old.decision_id * 2 + 1;
        END
        """
    )
    op.execute(
        "INSERT INTO knowledge_fts(rowid, kind, item_id, content) "
        "SELECT memory_id * 2, 'memory', memory_id, content FROM memory_revisions "
        "WHERE is_current = 1 AND content IS NOT NULL"
    )
    op.execute(
        "INSERT INTO knowledge_fts(rowid, kind, item_id, content) "
        "SELECT decision_id * 2 + 1, 'decision', decision_id, content FROM decision_revisions "
        "WHERE is_current = 1 AND content IS NOT NULL"
    )


def downgrade() -> None:
    """Downgrade schema.

    Drops only the FTS5 indexes and their sync triggers; every base table
    (``messages``, ``memories``, ``memory_revisions``, ``decisions``,
    ``decision_revisions``) and its data is left untouched.
    """
    op.execute("DROP TRIGGER IF EXISTS decision_revisions_fts_ad")
    op.execute("DROP TRIGGER IF EXISTS decision_revisions_fts_ai")
    op.execute("DROP TRIGGER IF EXISTS memory_revisions_fts_ad")
    op.execute("DROP TRIGGER IF EXISTS memory_revisions_fts_au")
    op.execute("DROP TRIGGER IF EXISTS memory_revisions_fts_ai")
    op.execute("DROP TABLE IF EXISTS knowledge_fts")
    op.execute("DROP TRIGGER IF EXISTS messages_fts_au")
    op.execute("DROP TRIGGER IF EXISTS messages_fts_ad")
    op.execute("DROP TRIGGER IF EXISTS messages_fts_ai")
    op.execute("DROP TABLE IF EXISTS message_fts")
