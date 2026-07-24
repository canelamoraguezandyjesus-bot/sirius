# Inventario técnico de la línea base — cierre de la sección 7 (ADR-001)

**Estado:** EVIDENCIA · no normativo · no modifica Sirius 0.1
**Fecha:** 24 de julio de 2026
**Fuente:** ejecución real, de solo lectura, sobre el repositorio `canelamoraguezandyjesus-bot/sirius`, rama `main`. Migraciones aplicadas contra una base SQLite temporal creada en `/tmp` para esta lectura; en ningún momento se ha tocado la base de datos real del usuario.
**Uso:** completa los cinco huecos que el documento `INVENTARIO_LINEA_BASE` (evidencia, sección 7) dejó pendientes de ejecución.

No se ha interpretado ni propuesto ningún cambio. No se ha modificado ningún archivo existente del repositorio, no se ha creado ninguna rama.

---

## 1. `alembic history --verbose` — cadena completa y head actual

Comando ejecutado: `uv run alembic history --verbose` (repositorio en su estado actual, sin aplicar nada).

**Head actual: `61be4bb269bf`** (create fts5 search indexes).

Cadena completa, de la más reciente a la base, con su padre (`Revises`):

| Revisión | Padre (`Revises`) | Contenido | Fecha |
|---|---|---|---|
| `61be4bb269bf` (head) | `94418c79da9d` | create fts5 search indexes | 2026-07-21 |
| `94418c79da9d` | `bf0ac43b986b` | add memory subject and project | 2026-07-19 |
| `bf0ac43b986b` | `05559a954593` | add message redaction | 2026-07-19 |
| `05559a954593` | `938fc6ac868c` | add decision supersession | 2026-07-19 |
| `938fc6ac868c` | `810c1563f6c6` | create decisions and decision revisions | 2026-07-18 |
| `810c1563f6c6` | `6f710ea6c2d2` | create events and link memory origin | 2026-07-18 |
| `6f710ea6c2d2` | `66951344e4b9` | create project revisions and lifecycle | 2026-07-17 |
| `66951344e4b9` | `0902e8217d75` | add project blockers | 2026-07-17 |
| `0902e8217d75` | `f5fb28ed426a` | create llm usage | 2026-07-12 |
| `f5fb28ed426a` | `bd39e7e3df5e` | add message operation_id and identity_version | 2026-07-12 |
| `bd39e7e3df5e` | `4022f15cc8df` | create identities and identity versions | 2026-07-12 |
| `4022f15cc8df` | `5ee754bfb0c2` | create memories and memory revisions | 2026-07-12 |
| `5ee754bfb0c2` | `c4d8fc9d6f51` | create projects | 2026-07-12 |
| `c4d8fc9d6f51` | `<base>` | create conversations and messages | 2026-07-12 |

Cadena lineal, sin ramas ni merges: cada revisión tiene exactamente un padre y (salvo el head) exactamente un hijo.

---

## 2. `sqlite_master` completo sobre una base temporal en `head`

Base temporal creada con `alembic upgrade head` (vacía, sin datos de usuario) y volcada con `SELECT type, name, tbl_name, sql FROM sqlite_master`.

### 2.1 Tablas reales (12) — DDL literal

```sql
CREATE TABLE alembic_version (
	version_num VARCHAR(32) NOT NULL,
	CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
)

CREATE TABLE conversations (
	id INTEGER NOT NULL,
	created_at DATETIME NOT NULL,
	is_main BOOLEAN NOT NULL,
	PRIMARY KEY (id)
)

CREATE TABLE decision_revisions (
	id INTEGER NOT NULL,
	decision_id INTEGER NOT NULL,
	version INTEGER NOT NULL,
	content TEXT NOT NULL,
	source_event_id INTEGER,
	is_current BOOLEAN NOT NULL,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(decision_id) REFERENCES decisions (id) ON DELETE CASCADE,
	FOREIGN KEY(source_event_id) REFERENCES events (id),
	CONSTRAINT uq_decision_revisions_decision_version UNIQUE (decision_id, version)
)

CREATE TABLE decisions (
	id INTEGER NOT NULL,
	subject TEXT NOT NULL,
	project_id INTEGER NOT NULL,
	status VARCHAR(16) NOT NULL,
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL, supersedes_decision_id INTEGER REFERENCES decisions (id),
	PRIMARY KEY (id),
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
)

CREATE TABLE events (
	id INTEGER NOT NULL,
	event_type TEXT NOT NULL,
	actor TEXT NOT NULL,
	message_id INTEGER,
	created_at DATETIME NOT NULL,
	redacted_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(message_id) REFERENCES messages (id) ON DELETE SET NULL
)

CREATE TABLE identities (
	id INTEGER NOT NULL,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id)
)

CREATE TABLE identity_versions (
	id INTEGER NOT NULL,
	identity_id INTEGER NOT NULL,
	version INTEGER NOT NULL,
	name TEXT NOT NULL,
	description TEXT NOT NULL,
	personality_instructions TEXT NOT NULL,
	is_current BOOLEAN NOT NULL,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(identity_id) REFERENCES identities (id) ON DELETE CASCADE,
	CONSTRAINT uq_identity_versions_identity_version UNIQUE (identity_id, version)
)

CREATE TABLE llm_usage (
	id INTEGER NOT NULL,
	year_month TEXT NOT NULL,
	spent_usd FLOAT NOT NULL,
	updated_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (year_month)
)

CREATE TABLE memories (
	id INTEGER NOT NULL,
	status VARCHAR(16) NOT NULL,
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL, subject_key TEXT, project_id INTEGER REFERENCES projects (id),
	PRIMARY KEY (id)
)

CREATE TABLE memory_revisions (
	id INTEGER NOT NULL,
	memory_id INTEGER NOT NULL,
	version INTEGER NOT NULL,
	content TEXT,
	origin TEXT NOT NULL,
	is_current BOOLEAN NOT NULL,
	created_at DATETIME NOT NULL, source_event_id INTEGER REFERENCES events (id),
	PRIMARY KEY (id),
	FOREIGN KEY(memory_id) REFERENCES memories (id) ON DELETE CASCADE,
	CONSTRAINT uq_memory_revisions_memory_version UNIQUE (memory_id, version)
)

CREATE TABLE "messages" (
	id INTEGER NOT NULL,
	conversation_id INTEGER NOT NULL,
	sequence INTEGER NOT NULL,
	role VARCHAR(16) NOT NULL,
	content TEXT,
	created_at DATETIME NOT NULL,
	operation_id TEXT,
	identity_version INTEGER,
	status VARCHAR(16) DEFAULT 'completed' NOT NULL,
	redacted_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT uq_messages_operation_role UNIQUE (conversation_id, operation_id, role),
	CONSTRAINT uq_messages_conversation_sequence UNIQUE (conversation_id, sequence),
	FOREIGN KEY(conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
)

CREATE TABLE project_revisions (
	id INTEGER NOT NULL,
	project_id INTEGER NOT NULL,
	version INTEGER NOT NULL,
	objective TEXT NOT NULL,
	state_summary TEXT NOT NULL,
	blockers_json TEXT NOT NULL,
	next_step TEXT NOT NULL,
	source_event_id INTEGER,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE,
	CONSTRAINT uq_project_revisions_project_version UNIQUE (project_id, version)
)

CREATE TABLE projects (
	id INTEGER NOT NULL,
	name TEXT NOT NULL,
	objective TEXT NOT NULL,
	current_state TEXT NOT NULL,
	next_step TEXT NOT NULL,
	is_active BOOLEAN NOT NULL,
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL, blockers TEXT DEFAULT '' NOT NULL, status VARCHAR(16) DEFAULT 'active' NOT NULL, completed_at DATETIME, current_revision_id INTEGER REFERENCES project_revisions (id),
	PRIMARY KEY (id)
)
```

### 2.2 Tablas virtuales FTS5 (2) y sus tablas-sombra internas

Hay **dos** mecanismos de búsqueda de texto completo, no uno:

- `knowledge_fts` — `CREATE VIRTUAL TABLE knowledge_fts USING fts5(kind UNINDEXED, item_id UNINDEXED, content)`. Tablas-sombra internas de SQLite/FTS5: `knowledge_fts_config`, `knowledge_fts_content`, `knowledge_fts_data`, `knowledge_fts_docsize`, `knowledge_fts_idx`.
- `message_fts` — `CREATE VIRTUAL TABLE message_fts USING fts5(content, content='messages', content_rowid='id')`. Tablas-sombra: `message_fts_config`, `message_fts_data`, `message_fts_docsize`, `message_fts_idx`. Esta es una tabla FTS5 en modo "external content" (usa `messages` como tabla de contenido, no guarda copia propia salvo el índice).

### 2.3 Índices

Únicos declarados explícitamente en migraciones:

- `uq_conversations_single_main` — `ON conversations (is_main) WHERE is_main = 1`
- `uq_projects_single_active` — `ON projects (is_active) WHERE is_active = 1`
- `uq_memory_revisions_single_current_per_memory` — `ON memory_revisions (memory_id) WHERE is_current = 1`
- `uq_decision_revisions_single_current_per_decision` — `ON decision_revisions (decision_id) WHERE is_current = 1`
- `uq_identity_versions_single_current_per_identity` — `ON identity_versions (identity_id) WHERE is_current = 1`

Más los autoíndices que SQLite crea para restricciones `UNIQUE`/`PRIMARY KEY` compuestas: `sqlite_autoindex_alembic_version_1`, `sqlite_autoindex_decision_revisions_1`, `sqlite_autoindex_identity_versions_1`, `sqlite_autoindex_llm_usage_1`, `sqlite_autoindex_memory_revisions_1`, `sqlite_autoindex_messages_1`, `sqlite_autoindex_messages_2`, `sqlite_autoindex_project_revisions_1`.

### 2.4 Triggers (8 en total)

**Sobre `memory_revisions`** (mantienen `knowledge_fts`, rowid = `memory_id * 2`):

```sql
CREATE TRIGGER memory_revisions_fts_ai AFTER INSERT ON memory_revisions
        WHEN new.is_current = 1 BEGIN
            DELETE FROM knowledge_fts WHERE rowid = new.memory_id * 2;
            INSERT INTO knowledge_fts(rowid, kind, item_id, content)
                SELECT new.memory_id * 2, 'memory', new.memory_id, new.content
                WHERE new.content IS NOT NULL;
        END

CREATE TRIGGER memory_revisions_fts_au AFTER UPDATE OF content ON memory_revisions
        WHEN new.is_current = 1 BEGIN
            DELETE FROM knowledge_fts WHERE rowid = new.memory_id * 2;
            INSERT INTO knowledge_fts(rowid, kind, item_id, content)
                SELECT new.memory_id * 2, 'memory', new.memory_id, new.content
                WHERE new.content IS NOT NULL;
        END

CREATE TRIGGER memory_revisions_fts_ad AFTER DELETE ON memory_revisions
        WHEN old.is_current = 1 BEGIN
            DELETE FROM knowledge_fts WHERE rowid = old.memory_id * 2;
        END
```

**Sobre `decision_revisions`** (mantienen `knowledge_fts`, rowid = `decision_id * 2 + 1`) — **solo INSERT y DELETE, no hay trigger de UPDATE**:

```sql
CREATE TRIGGER decision_revisions_fts_ai AFTER INSERT ON decision_revisions
        WHEN new.is_current = 1 BEGIN
            DELETE FROM knowledge_fts WHERE rowid = new.decision_id * 2 + 1;
            INSERT INTO knowledge_fts(rowid, kind, item_id, content)
                SELECT new.decision_id * 2 + 1, 'decision', new.decision_id, new.content
                WHERE new.content IS NOT NULL;
        END

CREATE TRIGGER decision_revisions_fts_ad AFTER DELETE ON decision_revisions
        WHEN old.is_current = 1 BEGIN
            DELETE FROM knowledge_fts WHERE rowid = old.decision_id * 2 + 1;
        END
```

**Sobre `messages`** (mantienen `message_fts`, mecanismo "external content" estándar de FTS5 — no tocan `knowledge_fts`):

```sql
CREATE TRIGGER messages_fts_ai AFTER INSERT ON messages BEGIN
            INSERT INTO message_fts(rowid, content) VALUES (new.id, new.content);
        END

CREATE TRIGGER messages_fts_ad AFTER DELETE ON messages BEGIN
            INSERT INTO message_fts(message_fts, rowid, content)
                VALUES('delete', old.id, old.content);
        END

CREATE TRIGGER messages_fts_au AFTER UPDATE ON messages BEGIN
            INSERT INTO message_fts(message_fts, rowid, content)
                VALUES('delete', old.id, old.content);
            INSERT INTO message_fts(rowid, content) VALUES (new.id, new.content);
        END
```

---

## 3. Esquema columna a columna, con nulabilidad, default y claves (`PRAGMA table_info` + `PRAGMA foreign_key_list`)

Formato de cada columna: `nombre — TIPO — {NOT NULL|NULL} — default={valor|ninguno} — {PK|}`.

### conversations
- `id` — INTEGER — NOT NULL — default=ninguno — PK
- `created_at` — DATETIME — NOT NULL — default=ninguno
- `is_main` — BOOLEAN — NOT NULL — default=ninguno

FKs: ninguna.

### messages
- `id` — INTEGER — NOT NULL — default=ninguno — PK
- `conversation_id` — INTEGER — NOT NULL — default=ninguno
- `sequence` — INTEGER — NOT NULL — default=ninguno
- `role` — VARCHAR(16) — NOT NULL — default=ninguno
- `content` — TEXT — NULL — default=ninguno
- `created_at` — DATETIME — NOT NULL — default=ninguno
- `operation_id` — TEXT — NULL — default=ninguno
- `identity_version` — INTEGER — NULL — default=ninguno
- `status` — VARCHAR(16) — NOT NULL — default=`'completed'`
- `redacted_at` — DATETIME — NULL — default=ninguno

FKs: `conversation_id → conversations.id` (ON DELETE CASCADE).

### projects
- `id` — INTEGER — NOT NULL — default=ninguno — PK
- `name` — TEXT — NOT NULL — default=ninguno
- `objective` — TEXT — NOT NULL — default=ninguno
- `current_state` — TEXT — NOT NULL — default=ninguno
- `next_step` — TEXT — NOT NULL — default=ninguno
- `is_active` — BOOLEAN — NOT NULL — default=ninguno
- `created_at` — DATETIME — NOT NULL — default=ninguno
- `updated_at` — DATETIME — NOT NULL — default=ninguno
- `blockers` — TEXT — NOT NULL — default=`''`
- `status` — VARCHAR(16) — NOT NULL — default=`'active'`
- `completed_at` — DATETIME — NULL — default=ninguno
- `current_revision_id` — INTEGER — NULL — default=ninguno

FKs: `current_revision_id → project_revisions.id` (sin acción en cascada).

### project_revisions
- `id` — INTEGER — NOT NULL — default=ninguno — PK
- `project_id` — INTEGER — NOT NULL — default=ninguno
- `version` — INTEGER — NOT NULL — default=ninguno
- `objective` — TEXT — NOT NULL — default=ninguno
- `state_summary` — TEXT — NOT NULL — default=ninguno
- `blockers_json` — TEXT — NOT NULL — default=ninguno
- `next_step` — TEXT — NOT NULL — default=ninguno
- `source_event_id` — INTEGER — NULL — default=ninguno
- `created_at` — DATETIME — NOT NULL — default=ninguno

FKs: `project_id → projects.id` (ON DELETE CASCADE). `source_event_id` **no tiene FK real declarada** en el esquema (es INTEGER simple, a diferencia de `memory_revisions.source_event_id` y `decision_revisions.source_event_id`, que sí son FK reales a `events.id`).

### memories
- `id` — INTEGER — NOT NULL — default=ninguno — PK
- `status` — VARCHAR(16) — NOT NULL — default=ninguno
- `created_at` — DATETIME — NOT NULL — default=ninguno
- `updated_at` — DATETIME — NOT NULL — default=ninguno
- `subject_key` — TEXT — NULL — default=ninguno
- `project_id` — INTEGER — NULL — default=ninguno

FKs: `project_id → projects.id` (sin acción en cascada).

### memory_revisions
- `id` — INTEGER — NOT NULL — default=ninguno — PK
- `memory_id` — INTEGER — NOT NULL — default=ninguno
- `version` — INTEGER — NOT NULL — default=ninguno
- `content` — TEXT — **NULL** — default=ninguno
- `origin` — TEXT — NOT NULL — default=ninguno
- `is_current` — BOOLEAN — NOT NULL — default=ninguno
- `created_at` — DATETIME — NOT NULL — default=ninguno
- `source_event_id` — INTEGER — NULL — default=ninguno

FKs: `memory_id → memories.id` (ON DELETE CASCADE); `source_event_id → events.id` (sin acción en cascada).

### events
- `id` — INTEGER — NOT NULL — default=ninguno — PK
- `event_type` — TEXT — NOT NULL — default=ninguno
- `actor` — TEXT — NOT NULL — default=ninguno
- `message_id` — INTEGER — NULL — default=ninguno
- `created_at` — DATETIME — NOT NULL — default=ninguno
- `redacted_at` — DATETIME — NULL — default=ninguno

FKs: `message_id → messages.id` (ON DELETE SET NULL).

### decisions
- `id` — INTEGER — NOT NULL — default=ninguno — PK
- `subject` — TEXT — NOT NULL — default=ninguno
- `project_id` — INTEGER — NOT NULL — default=ninguno
- `status` — VARCHAR(16) — NOT NULL — default=ninguno
- `created_at` — DATETIME — NOT NULL — default=ninguno
- `updated_at` — DATETIME — NOT NULL — default=ninguno
- `supersedes_decision_id` — INTEGER — NULL — default=ninguno

FKs: `project_id → projects.id` (ON DELETE CASCADE); `supersedes_decision_id → decisions.id` (autorreferencial, sin acción en cascada).

### decision_revisions
- `id` — INTEGER — NOT NULL — default=ninguno — PK
- `decision_id` — INTEGER — NOT NULL — default=ninguno
- `version` — INTEGER — NOT NULL — default=ninguno
- `content` — TEXT — **NOT NULL** — default=ninguno *(a diferencia de `memory_revisions.content`, aquí no es nulable — no hay marcador de "contenido borrado" a este nivel de esquema)*
- `source_event_id` — INTEGER — NULL — default=ninguno
- `is_current` — BOOLEAN — NOT NULL — default=ninguno
- `created_at` — DATETIME — NOT NULL — default=ninguno

FKs: `decision_id → decisions.id` (ON DELETE CASCADE); `source_event_id → events.id` (sin acción en cascada).

### identities
- `id` — INTEGER — NOT NULL — default=ninguno — PK
- `created_at` — DATETIME — NOT NULL — default=ninguno

FKs: ninguna.

### identity_versions
- `id` — INTEGER — NOT NULL — default=ninguno — PK
- `identity_id` — INTEGER — NOT NULL — default=ninguno
- `version` — INTEGER — NOT NULL — default=ninguno
- `name` — TEXT — NOT NULL — default=ninguno
- `description` — TEXT — NOT NULL — default=ninguno
- `personality_instructions` — TEXT — NOT NULL — default=ninguno
- `is_current` — BOOLEAN — NOT NULL — default=ninguno
- `created_at` — DATETIME — NOT NULL — default=ninguno

FKs: `identity_id → identities.id` (ON DELETE CASCADE). Restricción única compuesta `(identity_id, version)`.

### llm_usage
- `id` — INTEGER — NOT NULL — default=ninguno — PK
- `year_month` — TEXT — NOT NULL — default=ninguno — UNIQUE
- `spent_usd` — FLOAT — NOT NULL — default=ninguno
- `updated_at` — DATETIME — NOT NULL — default=ninguno

FKs: ninguna.

### alembic_version (tabla de housekeeping de Alembic, no de dominio)
- `version_num` — VARCHAR(32) — NOT NULL — default=ninguno — PK

FKs: ninguna.

---

## 4. Puntos del código que escriben o borran contenido (`UnitOfWork`, `delete_`, `redact_`, `archive_`)

Grep literal sobre `src/`, patrón `UnitOfWork|def delete_|def redact_|def archive_|\.delete_|\.redact_|\.archive_`. Archivo y línea:

```
src/sirius/adapters/persistence/sqlite_memory_repository.py:85:    ...SqliteUnitOfWork...
src/sirius/adapters/persistence/sqlite_memory_repository.py:223:    def archive_memory(self, memory_id: int) -> Memory:
src/sirius/adapters/persistence/sqlite_memory_repository.py:238:    def delete_memory(self, memory_id: int) -> Memory:
src/sirius/adapters/persistence/sqlite_memory_repository.py:270:    """Bind a repository to an externally owned session (used by ``SqliteUnitOfWork``)."""
src/sirius/adapters/persistence/sqlite_event_repository.py:45:    ...SqliteUnitOfWork...
src/sirius/adapters/persistence/sqlite_event_repository.py:104:    """Bind a repository to an externally owned session (used by ``SqliteUnitOfWork``)."""
src/sirius/adapters/persistence/sqlite_unit_of_work.py:1:"""SQLite-backed ``UnitOfWork``: one session/transaction shared by its repositories.
src/sirius/adapters/persistence/sqlite_unit_of_work.py:39:__all__ = ["SqliteUnitOfWork", "build_sqlite_unit_of_work"]
src/sirius/adapters/persistence/sqlite_unit_of_work.py:42:class SqliteUnitOfWork:
src/sirius/adapters/persistence/sqlite_unit_of_work.py:105:def build_sqlite_unit_of_work(database_path: Path) -> SqliteUnitOfWork:
src/sirius/adapters/persistence/sqlite_unit_of_work.py:109:    return SqliteUnitOfWork(session_factory, engine)
src/sirius/main.py:50:        archive_memory_use_case=dependencies.archive_memory_use_case,
src/sirius/main.py:51:        delete_memory_use_case=dependencies.delete_memory_use_case,
src/sirius/main.py:56:        archive_decision_use_case=dependencies.archive_decision_use_case,
src/sirius/adapters/persistence/sqlite_conversation_repository.py:59:    ...SqliteUnitOfWork...
src/sirius/adapters/persistence/sqlite_conversation_repository.py:180:    def redact_message(self, message_id: int) -> Message:
src/sirius/adapters/persistence/sqlite_conversation_repository.py:202:    """Bind a repository to an externally owned session (used by ``SqliteUnitOfWork``)."""
src/sirius/adapters/persistence/sqlite_decision_repository.py:83:    ...SqliteUnitOfWork...
src/sirius/adapters/persistence/sqlite_decision_repository.py:202:    def archive_decision(self, decision_id: int) -> Decision:
src/sirius/adapters/persistence/sqlite_decision_repository.py:253:    """Bind a repository to an externally owned session (used by ``SqliteUnitOfWork``)."""
src/sirius/presentation/knowledge_widget.py:12:``UnitOfWork``, SQLAlchemy, or SQLite directly (AGENTS.md: dependency...)
src/sirius/presentation/knowledge_widget.py:48:from sirius.application.archive_decision import (
src/sirius/presentation/knowledge_widget.py:52:from sirius.application.archive_memory import ArchiveMemoryUseCase, MemoryNotArchivableError
src/sirius/presentation/knowledge_widget.py:59:from sirius.application.delete_memory import (
src/sirius/presentation/knowledge_widget.py:135:        self.redact_radio = QRadioButton("Redactar también el mensaje fuente")
src/sirius/presentation/knowledge_widget.py:143:        self.redact_radio.toggled.connect(self._enable_ok_once_chosen)
src/sirius/presentation/knowledge_widget.py:150:        layout.addWidget(self.redact_radio)
src/sirius/presentation/knowledge_widget.py:161:            if self.redact_radio.isChecked()
src/sirius/presentation/knowledge_widget.py:308:        self.archive_memory_button = QPushButton("Archivar")
src/sirius/presentation/knowledge_widget.py:309:        self.archive_memory_button.clicked.connect(self._handle_archive_memory_clicked)
src/sirius/presentation/knowledge_widget.py:310:        self.delete_memory_button = QPushButton("Eliminar…")
src/sirius/presentation/knowledge_widget.py:311:        self.delete_memory_button.clicked.connect(self._handle_delete_memory_clicked)
src/sirius/presentation/knowledge_widget.py:318:        buttons_row.addWidget(self.archive_memory_button)
src/sirius/presentation/knowledge_widget.py:319:        buttons_row.addWidget(self.delete_memory_button)
src/sirius/presentation/knowledge_widget.py:451:        self.archive_decision_button = QPushButton("Archivar")
src/sirius/presentation/knowledge_widget.py:452:        self.archive_decision_button.clicked.connect(self._handle_archive_decision_clicked)
src/sirius/presentation/knowledge_widget.py:460:        buttons_row.addWidget(self.archive_decision_button)
src/sirius/presentation/knowledge_widget.py:704:            self.archive_memory_button,
src/sirius/presentation/knowledge_widget.py:705:            self.delete_memory_button,
src/sirius/presentation/knowledge_widget.py:710:            self.archive_decision_button,
src/sirius/presentation/validated_main_window.py:12:from sirius.application.archive_decision import ArchiveDecisionUseCase
src/sirius/presentation/validated_main_window.py:13:from sirius.application.archive_memory import ArchiveMemoryUseCase
src/sirius/presentation/validated_main_window.py:18:from sirius.application.delete_memory import DeleteMemoryUseCase
src/sirius/presentation/main_window.py:33:from sirius.application.archive_decision import ArchiveDecisionUseCase
src/sirius/presentation/main_window.py:34:from sirius.application.archive_memory import ArchiveMemoryUseCase
src/sirius/presentation/main_window.py:39:from sirius.application.delete_memory import DeleteMemoryUseCase
src/sirius/presentation/main_window.py:1193:            self._api_key_settings_use_case.delete_key()
src/sirius/ports/unit_of_work.py:3:SIRIUS-ARQ-0.1 S4 defines ``UnitOfWork`` as ``begin()``, ``commit()``,
src/sirius/ports/unit_of_work.py:31:__all__ = ["UnitOfWork"]
src/sirius/ports/unit_of_work.py:34:class UnitOfWork(Protocol):
src/sirius/application/archive_memory.py:13:``MemoryRepository``, ``EventRepository``, ``UnitOfWork``, SQLAlchemy, or
src/sirius/application/archive_memory.py:21:the status change are written through the same ``UnitOfWork`` and committed
src/sirius/application/archive_memory.py:23:``UnitOfWork.__exit__`` rolls back everything — never an orphan event, never
src/sirius/application/archive_memory.py:31:from sirius.ports.unit_of_work import UnitOfWork
src/sirius/application/archive_memory.py:51:    def __init__(self, unit_of_work: UnitOfWork) -> None:
src/sirius/application/archive_memory.py:86:            archived = uow.memory_repository.archive_memory(memory_id)
src/sirius/ports/memory_repository.py:68:    def archive_memory(self, memory_id: int) -> Memory:
src/sirius/ports/memory_repository.py:72:    def delete_memory(self, memory_id: int) -> Memory:
src/sirius/domain/event.py:12:...``ConversationRepository.redact_message``...
src/sirius/ports/decision_repository.py:83:    def archive_decision(self, decision_id: int) -> Decision:
src/sirius/application/archive_decision.py:24:the status change are written through the same ``UnitOfWork`` and committed
src/sirius/application/archive_decision.py:26:``UnitOfWork.__exit__`` rolls back everything.
src/sirius/application/archive_decision.py:33:from sirius.ports.unit_of_work import UnitOfWork
src/sirius/application/archive_decision.py:53:    def __init__(self, unit_of_work: UnitOfWork) -> None:
src/sirius/application/archive_decision.py:84:            archived = uow.decision_repository.archive_decision(decision_id)
src/sirius/ports/conversation_repository.py:53:    def redact_message(self, message_id: int) -> Message:
src/sirius/ports/secrets.py:31:    def delete_secret(self, key: str) -> None:
src/sirius/application/correct_memory.py:6:``EventRepository``, ``UnitOfWork``, SQLAlchemy, or SQLite directly
src/sirius/application/correct_memory.py:21:through the same ``UnitOfWork`` and committed together; any failure at any
src/sirius/application/correct_memory.py:22:point leaves the transaction uncommitted, so ``UnitOfWork.__exit__`` rolls
src/sirius/application/correct_memory.py:31:from sirius.ports.unit_of_work import UnitOfWork
src/sirius/application/correct_memory.py:61:    def __init__(self, unit_of_work: UnitOfWork) -> None:
src/sirius/application/supersede_decision.py:24:through the same ``UnitOfWork`` and committed together; any failure leaves
src/sirius/application/supersede_decision.py:34:from sirius.ports.unit_of_work import UnitOfWork
src/sirius/application/supersede_decision.py:59:    def __init__(self, unit_of_work: UnitOfWork) -> None:
src/sirius/application/api_key_settings.py:43:    def delete_key(self) -> None:
src/sirius/application/api_key_settings.py:45:            self._secret_store.delete_secret(OPENAI_API_KEY_SECRET_NAME)
src/sirius/application/propose_decision.py:14:first revision are written through the same ``UnitOfWork`` and committed
src/sirius/application/propose_decision.py:22:from sirius.ports.unit_of_work import UnitOfWork
src/sirius/application/propose_decision.py:37:    def __init__(self, unit_of_work: UnitOfWork) -> None:
src/sirius/composition_root.py:54:from sirius.application.archive_decision import ArchiveDecisionUseCase
src/sirius/composition_root.py:55:from sirius.application.archive_memory import ArchiveMemoryUseCase
src/sirius/composition_root.py:61:from sirius.application.delete_memory import DeleteMemoryUseCase
src/sirius/application/approve_decision.py:15:decision's status change are written through the same ``UnitOfWork`` and
src/sirius/application/approve_decision.py:24:from sirius.ports.unit_of_work import UnitOfWork
src/sirius/application/approve_decision.py:49:    def __init__(self, unit_of_work: UnitOfWork) -> None:
src/sirius/application/delete_memory.py:30:``MemoryRepository.delete_memory`` (V4/B4d, already used by the SQLite
src/sirius/application/delete_memory.py:43:content redaction are all written through the same ``UnitOfWork`` and
src/sirius/application/delete_memory.py:57:from sirius.ports.unit_of_work import UnitOfWork
src/sirius/application/delete_memory.py:112:    def __init__(self, unit_of_work: UnitOfWork) -> None:
src/sirius/application/delete_memory.py:172:                    uow.conversation_repository.redact_message(source_message_id)
src/sirius/application/delete_memory.py:174:            deleted = uow.memory_repository.delete_memory(memory_id)
src/sirius/application/delete_memory.py:180:    def _resolve_source_message_id(uow: UnitOfWork, memory: Memory) -> int | None:
src/sirius/application/save_manual_memory.py:5:``UnitOfWork``, SQLAlchemy, or SQLite directly (AGENTS.md: dependency
src/sirius/application/save_manual_memory.py:17:through the same ``UnitOfWork``, and ``commit()`` runs only after both writes
src/sirius/application/save_manual_memory.py:19:so ``UnitOfWork.__exit__`` rolls back everything — never an orphan event,
src/sirius/application/save_manual_memory.py:31:from sirius.ports.unit_of_work import UnitOfWork
```

Puntos de implementación real que ejecutan un borrado o redacción (no solo referencias/imports/comentarios):

- `src/sirius/adapters/persistence/sqlite_memory_repository.py:223` — `archive_memory`
- `src/sirius/adapters/persistence/sqlite_memory_repository.py:238` — `delete_memory` (pone `content` a NULL en todas las revisiones)
- `src/sirius/adapters/persistence/sqlite_decision_repository.py:202` — `archive_decision`
- `src/sirius/adapters/persistence/sqlite_conversation_repository.py:180` — `redact_message`
- `src/sirius/application/delete_memory.py:172` — llama a `redact_message` sobre el mensaje fuente, dentro de la misma `UnitOfWork`
- `src/sirius/application/delete_memory.py:174` — llama a `delete_memory` sobre la memoria, dentro de la misma `UnitOfWork`
- `src/sirius/application/archive_memory.py:86` — llama a `archive_memory`
- `src/sirius/application/archive_decision.py:84` — llama a `archive_decision`
- `src/sirius/application/api_key_settings.py:45` — `delete_key` → `delete_secret` (fuera de SQLite, en el `SecretStore`/keyring)
- `src/sirius/ports/secrets.py:31` — contrato `delete_secret` del puerto `SecretStore`

No hay ningún `delete_decision` ni ruta de borrado de decisiones en el código: confirma lo que el documento de evidencia ya afirmaba en la sección 5 ("No existe borrado de decisiones").

---

## 5. Tiempo de `alembic upgrade head` sobre base temporal

Ejecutado sobre una base SQLite temporal, vacía, recién creada (sin datos de usuario), aplicando las 14 migraciones desde `<base>` hasta `61be4bb269bf`:

```
TIEMPO alembic upgrade head sobre base temporal vacia: 0.9739 s
```

Este tiempo corresponde a una base vacía; no representa el tiempo de migración sobre una base con volumen real de datos de usuario (ese dato no está disponible sin una base de usuario real, y no se ha tocado la del usuario para obtenerlo).

---

## 6. Hallazgos adicionales de la lectura directa (no estaban en el documento de evidencia previo)

Datos observados durante esta ejecución que no aparecían en las secciones 1–6 del documento de evidencia y que son relevantes como inventario físico, sin interpretarlos para ADR-001:

1. **Hay dos mecanismos FTS, no uno.** `message_fts` (sobre `messages.content`, modo "external content" de FTS5, con sus tres triggers `messages_fts_ai/ad/au`) es independiente de `knowledge_fts` (sobre memorias y decisiones). El documento de evidencia solo describía `knowledge_fts`.
2. **`decision_revisions` no tiene trigger de UPDATE** hacia `knowledge_fts` (solo `_ai` y `_ad`); `memory_revisions` sí tiene los tres (`_ai`, `_au`, `_ad`). Asimetría real en el esquema.
3. **`decision_revisions.content` es `NOT NULL`**, a diferencia de `memory_revisions.content` (nullable). No existe a nivel de esquema un mecanismo de "borrado" de contenido de decisión equivalente al de memoria — consistente con "no existe borrado de decisiones" (sección 5 del documento de evidencia), pero es la primera vez que queda confirmado a nivel de columna.
4. **FK reales adicionales no mencionadas en el documento de evidencia:**
   - `projects.current_revision_id → project_revisions.id`
   - `memories.project_id → projects.id`
   - `decisions.project_id → projects.id` (ON DELETE CASCADE)
5. **`project_revisions.source_event_id` es un `INTEGER` simple, sin FK declarada** — a diferencia de `memory_revisions.source_event_id` y `decision_revisions.source_event_id`, que sí son FK reales a `events.id`. Asimetría real en el esquema, no interpretada aquí.

Nada de lo anterior cambia la decisión de ADR-001; es evidencia física adicional para su expediente de migración.
