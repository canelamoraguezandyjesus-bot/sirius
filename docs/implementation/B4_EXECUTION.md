# B4 — Plan de ejecución operativo

## Estado y autoridad

El usuario autorizó explícitamente el 18 de julio de 2026 dividir B4 para reducir riesgo, tamaño de diff y tiempo de revisión.

Esta división es exclusivamente operativa. No cambia la Definición de Producto, la Arquitectura Técnica, las ATD ni los requisitos aprobados. B4 continúa cerrando D-03 y cubriendo RF-019 a RF-026 y PA-010 a PA-016.

Estado inicial: **AUTORIZADO Y NO INICIADO**.

## Objetivo de B4

Completar la capacidad observable de eventos, recuerdos y decisiones para que Sirius pueda:

- guardar memoria solo por orden o confirmación explícita;
- conservar y abrir un origen consultable;
- distinguir exploración, propuesta y decisión aprobada;
- corregir y sustituir sin destruir el historial;
- archivar y eliminar según la política aprobada;
- detectar incompatibilidades y no resolverlas silenciosamente.

## Base ya implementada

B4 no parte de cero. V4 ya incluye:

- recuerdo genérico versionado;
- origen obligatorio como valor no vacío;
- corrección mediante revisión nueva;
- archivo;
- redacción del contenido estructurado al eliminar.

Los subbloques siguientes deben reutilizar y completar esa infraestructura. No deben crear un segundo sistema de memoria paralelo.

## Reglas comunes

- Una rama y una pull request por subbloque.
- Ejecución secuencial al principio; no trabajar dos subbloques de B4 en paralelo.
- Cada cambio debe enlazar requisitos, pruebas y archivos afectados.
- No ampliar el modelo conceptual aprobado: evento, mensaje, recuerdo, decisión y proyecto.
- No introducir guardado proactivo, embeddings, RAG, grafos ni multiagente.
- No modificar documentos canónicos.
- No declarar superadas pruebas manuales o con proveedor real.
- `scripts/check.ps1` y CI deben quedar verdes antes del merge.
- Máximo dos ciclos de revisión y corrección por PR. Si no converge, devolver `BLOCKED_BY_DECISION`.
- El usuario conserva la autorización de merge.

## B4a — Origen consultable y guardado manual

### Alcance

- Representación persistente del evento de origen aprobado por la arquitectura.
- Enlace real entre recuerdo y evento o mensaje de procedencia.
- Caso de uso explícito para guardar un recuerdo manual.
- Consulta del origen sin acceso directo de la interfaz a SQLite.
- Fecha, estado y versión observables.

### Trazabilidad

- RF-019 — Guardar recuerdo.
- RF-021 — Consultar origen.
- PA-010 — Guardar memoria manual.

### Resultado verificable

Al ordenar guardar una preferencia o un hecho, se crea un recuerdo con origen, fecha, estado y versión, y el origen puede consultarse posteriormente.

### Fuera de alcance

- decisiones;
- sustitución;
- conflictos;
- archivo o eliminación desde interfaz;
- búsqueda FTS5 general;
- panel de contexto completo de B5.

## B4b — Decisiones y aprobación explícita

### Alcance

- Tipo o entidad de decisión sobre la infraestructura de conocimiento existente.
- Asunto, proyecto, estado, versión, fecha y origen.
- Estados mínimos necesarios para propuesta y aprobación.
- Caso de uso que exige confirmación explícita para aprobar.
- Una exploración conversacional no crea una decisión aprobada.

### Trazabilidad

- RF-020 — Guardar decisión.
- PA-011 — No convertir exploración en decisión aprobada.

### Resultado verificable

Debatir alternativas no genera una decisión aprobada. Una aprobación explícita sí crea o activa la decisión correspondiente con su origen y versión.

### Fuera de alcance

- sustitución de otra decisión;
- precedencia frente a recuerdos;
- resolución de conflictos;
- panel de contexto de B5.

## B4c — Corrección y sustitución

### Alcance

- Consolidar la corrección existente bajo los contratos vigentes.
- Nueva revisión inmutable y puntero autoritativo a la vigente.
- Relación explícita de sustitución entre decisiones.
- Exclusión de revisiones sustituidas del contexto normal.
- Consulta histórica sin tratar versiones anteriores como vigentes.

### Trazabilidad

- RF-022 — Corregir.
- RF-023 — Sustituir.
- PA-012 — Corregir y versionar.
- PA-013 — Sustituir decisión.

### Resultado verificable

Una corrección mantiene la versión anterior como histórica y activa la nueva. Una decisión sustituta queda enlazada con la sustituida y solo la nueva entra en el contexto ordinario.

## B4d — Archivo, eliminación y redacción de origen

### Alcance

- Archivo consultable fuera del contexto ordinario.
- Eliminación con confirmación explícita.
- Borrado del contenido estructurado y de sus índices.
- Conservación del marcador mínimo sin contenido.
- Elección explícita de redactar o conservar el mensaje fuente.
- Advertencia de que una copia antigua puede reintroducir datos eliminados.

### Trazabilidad

- RF-024 — Archivar.
- RF-025 — Eliminar.
- PA-015 — Archivar.
- PA-016 — Eliminar.
- SP-06 — Borrado y copia antigua.

### Resultado verificable

Un elemento archivado sigue siendo consultable y deja de usarse normalmente. Un elemento eliminado pierde su contenido conforme a la opción elegida y solo conserva el marcador mínimo autorizado.

## B4e — Precedencia y conflictos

### Alcance

- Detección determinista de recuerdos vigentes incompatibles del mismo asunto.
- Prioridad de una decisión aprobada vigente sobre recuerdos generales incompatibles del mismo asunto.
- Solicitud de aclaración cuando no exista precedencia inequívoca.
- Prohibición de elegir silenciosamente.
- Pruebas de dominio y aplicación independientes del proveedor real.

### Trazabilidad

- RF-026 — Detectar conflicto.
- PA-014 — Conflicto.
- DR-011 — Precedencia y conflictos de memoria.

### Resultado verificable

Ante dos recuerdos incompatibles sin precedencia, Sirius devuelve un conflicto explícito y solicita aclaración. Cuando existe una decisión aprobada vigente del mismo asunto, esa decisión prevalece de forma trazable.

## B4f — Integración observable y cierre de B4

### Alcance

- Integrar las operaciones aprobadas en las superficies existentes sin crear una aplicación de gestión independiente.
- Completar casos de uso, composición, interfaz mínima y pruebas GUI necesarias.
- Añadir indexación o búsqueda local únicamente en la medida necesaria para PA-010 a PA-016 y para el posterior B6.
- Actualizar la documentación operativa y la matriz de evidencia.

### Trazabilidad

- PA-010 a PA-016 completas.
- Parte correspondiente de PA-008 y PA-E2E-01 preparada, sin declararla formalmente superada mientras dependa de proveedor real o evaluación humana.

## Puerta de entrada de cada subbloque

Antes de comenzar:

1. El subbloque anterior está fusionado y CI está verde.
2. La tarea identifica requisitos y pruebas exactas.
3. Se ha inspeccionado el código existente para evitar duplicación.
4. El diff previsto está acotado y no requiere una decisión nueva.
5. La rama parte del `main` vigente.

## Criterio de cierre de cada subbloque

Un subbloque queda `READY_FOR_HUMAN_REVIEW` cuando:

- cumple exclusivamente su alcance;
- añade o actualiza las pruebas previstas;
- `scripts/check.ps1` pasa;
- CI está verde;
- no quedan hallazgos `BLOCKER` o `HIGH`;
- la documentación operativa coincide con el comportamiento;
- la PR explica límites y pendientes;
- no se han declarado superadas pruebas manuales no ejecutadas.

## Estados finales permitidos

- `READY_FOR_HUMAN_REVIEW`
- `BLOCKED_BY_DECISION`
- `FAILED_SAFELY`
- `USAGE_LIMIT_REACHED`

## Criterio de cierre de B4 completo

B4 solo podrá marcarse terminado cuando:

- B4a a B4f estén fusionados;
- RF-019 a RF-026 tengan trazabilidad verificable;
- PA-010 a PA-016 existan y pasen en la parte automatizable;
- no queden defectos bloqueantes o altos de D-03;
- las revisiones históricas, archivadas, sustituidas o eliminadas no entren indebidamente en el contexto vigente;
- la documentación operativa y el registro de evidencia estén actualizados;
- el usuario haya autorizado todos los merges.

## Primera tarea funcional

La primera tarea funcional de esta secuencia fue **B4a — origen consultable y guardado manual**.

La prueba de humo cloud definida en `docs/implementation/CLOUD_SMOKE_TEST.md` terminó en `CLOUD_SMOKE_PASSED` el 18 de julio de 2026 (evidencia en `docs/implementation/CLOUD_SMOKE_EVIDENCE_20260718.md`, PR #34 fusionada). La puerta de entrada de B4a quedó satisfecha y B4a se implementó el 18 de julio de 2026 (rama `claude/intelligent-bohr-1s38y6`, PR #36). La revisión de Fase C encontró un `BLOCKER` transaccional (evento y recuerdo en dos transacciones independientes), corregido en la misma rama y PR mediante `UnitOfWork` (ver `AUTOMATION_OPERATING_CONTRACT.md` §2). **B4a quedó fusionado en `main`** el 18 de julio de 2026 (commit `c025683c960a19a1a9c1aa40fa861547026118cc`), con el workflow `Quality` en verde sobre ese commit.

**B4b — decisiones y aprobación explícita** se implementó el 18 de julio de 2026 sobre el `main` ya fusionado de B4a, siguiendo el mismo patrón que B4a: entidad de decisión (`sirius.domain.decision`), tabla `decisions`/`decision_revisions` (migración Alembic no destructiva), `DecisionRepository`/`SqliteDecisionRepository`, extensión mínima de `UnitOfWork` con `decision_repository`, `ProposeDecisionUseCase` (propuesta) y `ApproveDecisionUseCase` (aprobación con confirmación explícita obligatoria), y `GetDecisionOriginUseCase` (consulta de asunto, proyecto, estado, versión, fecha y origen). Una PR borrador quedó abierta hacia `main`, pendiente de revisión y sin merge. El usuario decidió expresamente, el 18 de julio de 2026, activar desde esta PR la revisión automática solicitada mediante una incidencia GitHub etiquetada `agent-review-requested` — ver `AUTOMATION_OPERATING_CONTRACT.md` §2 y §10 para el registro completo de esa decisión y sus límites.

**Estado real verificado antes de iniciar B4c:** la PR #37 (B4b) quedó **fusionada en `main`** el 18 de julio de 2026 (commit de merge `d1bbb872751a96ca11ec38c20fd8b3fb5322651c`), con el workflow `Quality` en verde (669 pruebas). Verificado directamente sobre `origin/main` (no solo por resumen previo) antes de tocar código de B4c.

**B4c — Corrección y sustitución** se implementó el 18 de julio de 2026 sobre el `main` ya fusionado de B4b, reutilizando la infraestructura existente sin crear un segundo sistema de memoria, decisiones o eventos:

- *Corrección de recuerdos (RF-022, PA-012):* `CorrectMemoryUseCase` (`sirius.application.correct_memory`) consolida la corrección ya existente desde V4 (`MemoryRepository.correct_memory`, que ya creaba una revisión nueva inmutable, movía el puntero `current_revision` y conservaba la revisión anterior) bajo el mismo contrato transaccional que B4a estableció para la creación: valida contenido y estado corregible antes de escribir nada, crea un evento de origen (`memory.corrected`) y la nueva revisión dentro de la misma `UnitOfWork`, y solo confirma si ambos escriben con éxito. Un identificador inexistente o un estado no corregible (archivado/eliminado) falla de forma segura sin escribir nada; un fallo tras crear el evento revierte también el evento.
- *Sustitución de decisiones (RF-023, PA-013):* nuevo estado `DecisionStatus.SUPERSEDED` y campo `Decision.supersedes_decision_id` (el equivalente, a la granularidad de decisión que B4b ya eligió, del `knowledge_revision.supersedes_revision_id` de la Arquitectura Técnica aprobada S7.3 — B4b nunca da a una decisión más de una revisión, así que el enlace de sustitución vive entre dos decisiones, no entre dos revisiones). `SupersedeDecisionUseCase` (`sirius.application.supersede_decision`) exige confirmación explícita (aprueba la sustituta como parte de la misma operación), valida ambas decisiones existentes, que la sustituida esté APPROVED, que la sustituta esté PROPOSED, que no sea autosustitución y que compartan asunto y proyecto, y ejecuta evento + aprobación de la sustituta + estado histórico de la sustituida + enlace de sustitución en una sola `UnitOfWork`. `DecisionRepository.supersede_decision`/`list_current_decisions` (consulta ordinaria de decisiones vigentes, excluye propuestas y sustituidas)/`get_superseding_decision` (consulta inversa del enlace).
- *Persistencia:* migración Alembic aditiva y no destructiva `05559a954593` (`decisions.supersedes_decision_id`, columna nula con clave foránea autorreferencial); ningún dato existente se pierde ni se reescribe.
- *Pruebas:* Ruff, mypy y pytest en verde (735 pruebas: 669 previas + 66 nuevas), incluidas atomicidad/rollback de ambas operaciones, migración real (`upgrade`/`downgrade`), regresión de B4a/B4b, y la garantía de que una conversación ordinaria nunca corrige ni sustituye por sí sola.

La PR #39 quedó **fusionada en `main`** el 19 de julio de 2026 (commit `e244649affd11e6e1bdb8179adb00d2b6d610f7e`, workflow `Quality` en verde). Verificado directamente sobre `origin/main` (no solo por resumen) antes de iniciar B4d.

**B4d — Archivo, eliminación y redacción de origen** se implementó el 19 de julio de 2026 sobre el `main` ya fusionado de B4c, reutilizando la infraestructura existente sin crear un segundo sistema de memoria, decisiones o eventos:

- *Archivo (RF-024, PA-015):* `ArchiveMemoryUseCase` (`sirius.application.archive_memory`) consolida, bajo el mismo contrato transaccional de B4a/B4c, el archivo que `MemoryRepository.archive_memory` ya implementaba desde V4 (cambia `Memory.status` a `ARCHIVED`, conserva contenido, revisiones y origen); valida existencia y estado antes de escribir, crea un evento de auditoría (`memory.archived`) y solo entonces cambia el estado, todo dentro de la misma `UnitOfWork`. `ArchiveDecisionUseCase` (`sirius.application.archive_decision`) hace lo mismo para decisiones: nuevo estado `DecisionStatus.ARCHIVED` (cuarto y último de la enumeración de Producto S6), alcanzable solo desde `APPROVED` (`sirius.domain.decision.ensure_can_archive`, mirroring `sirius.domain.memory.ensure_can_archive`). `MemoryRepository.list_archived_memories()`/`DecisionRepository.list_archived_decisions()` son las consultas explícitas de archivados que RF-024 exige; `list_current_memories()`/`list_current_decisions()` (ya existentes) siguen excluyéndolos sin cambios.
- *Eliminación (RF-025, PA-016, SP-06):* `DeleteMemoryUseCase` (`sirius.application.delete_memory`) exige `confirmed=True` y una elección explícita y tipada sobre el mensaje fuente (`sirius.domain.conversation.SourceMessageChoice.PRESERVE`/`REDACT`, parámetro obligatorio sin valor por defecto: omitirlo falla con `TypeError` antes de que el cuerpo del método se ejecute; un valor no válido falla con `InvalidSourceMessageChoiceError`) — ambas comprobaciones ocurren antes de abrir cualquier transacción. Reutiliza `MemoryRepository.delete_memory()` (V4: redacta `content` a `NULL` en todas las revisiones de la historia, no solo la vigente, conservando id/versión/origen/fecha como marcador mínimo) y, cuando se elige redactar, `ConversationRepository.redact_message()` (nuevo: `content` a `NULL`, `status` a `REDACTED`, `redacted_at` con marca de tiempo — nunca toca otro mensaje). El mensaje fuente se resuelve a partir del evento de origen de la revisión vigente (`memory.current_revision.source_event_id`); si no existe (recuerdo anterior a B4a, o evento sin mensaje enlazado), redactar es una operación seleccionable pero segura, sin efecto (no falla). El evento de auditoría (`memory.deleted`), la redacción del mensaje (si se eligió) y el borrado de contenido de la memoria ocurren en ese orden, dentro de la misma `UnitOfWork`: un fallo en cualquier paso revierte los anteriores. `DeleteMemoryUseCase.delete()` devuelve, junto al recuerdo eliminado, la advertencia aprobada (SP-06/DR-012) de que restaurar una copia antigua puede reintroducir información eliminada. La eliminación de decisiones queda deliberadamente fuera de este corte: ni PA-016 ni la enumeración de estados de decisión de Producto S6 la mencionan (a diferencia de "archivada", que sí aparece explícitamente) — `sirius.domain.decision` documenta esta lectura de las fuentes en su docstring de módulo.
- *Persistencia:* migración Alembic `bf0ac43b986b` (revisa `05559a954593`): añade `messages.redacted_at` (columna nueva, nula) y relaja `messages.content` de `NOT NULL` a nulo mediante `batch_alter_table` (SQLite no soporta `ALTER COLUMN` fuera de modo por lotes; mismo patrón que `f5fb28ed426a` ya usó en esta misma tabla para su restricción única). Ningún mensaje existente se pierde ni cambia de valor; `redacted_at` queda `NULL` en todo mensaje previo, correcto porque ninguno fue redactado antes de esta migración. Los estados nuevos (`MemoryStatus`/`DecisionStatus`/`MessageStatus` ya existentes con columnas `VARCHAR` sin `CHECK`) no requieren migración adicional.
- *Pruebas:* Ruff, mypy y pytest en verde (830 pruebas: 735 previas + 95 nuevas), incluidas atomicidad/rollback de las tres operaciones (archivo de recuerdo, archivo de decisión, eliminación con y sin redacción del mensaje fuente), migración real (`upgrade`/`downgrade`, preservación de datos previos), ciclo de vida de extremo a extremo con SQLite real (incluida persistencia tras cerrar/reabrir), exclusión de contenido redactado de un `Context` reconstruido, y la garantía de que una conversación ordinaria nunca archiva ni elimina por sí sola.

Una PR borrador quedó abierta hacia `main`, pendiente de revisión y sin merge. A diferencia de B4b y B4c, **esta ejecución no está autorizada a activar la revisión automática por incidencia `agent-review-requested`**: la autorización operativa registrada en `AUTOMATION_OPERATING_CONTRACT.md` §10 fue puntual para las transiciones B4a→B4b y B4b→B4c y no se extendió a B4d en este encargo.

**Estado real verificado antes de iniciar B4e:** B4d quedó fusionado en `main` (commit de merge `031dcc0`, PR #41). Verificado directamente sobre `origin/main` (main en `e94d129`, incluyendo además la evidencia de humo de automatización, PR #48) antes de tocar código de B4e.

**B4e — Precedencia y conflictos** se implementó el 19 de julio de 2026 sobre el `main` ya fusionado de B4d, bajo la autorización general de `AUTOMATION_OPERATING_CONTRACT.md` v1.1 (§1, vigente tras el merge de la PR #44), reutilizando la infraestructura existente sin crear un segundo sistema de memoria, decisiones o eventos:

- *Identificación de asunto (RF-026, DR-011):* `Memory` gana `subject_key: str | None`/`project_id: int | None`, ambos opcionales y fijados solo al crear (inmutables a través de correcciones, igual que `Decision.subject`/`project_id`) — la contraparte, en `Memory`, de los campos que `Decision` ya tenía desde B4b. Migración Alembic aditiva y reversible `43406702d62c` (`memories.subject_key`, `memories.project_id` con `ON DELETE SET NULL`); todo recuerdo anterior a B4e migra con ambos campos en `NULL`, íntegro y legible.
- *Regla de precedencia y conflicto (RF-026, PA-014, DR-011):* `sirius.domain.knowledge_precedence.resolve_memory_precedence`, función pura y determinista: compara únicamente recuerdos `CURRENT` y decisiones `APPROVED` que comparten `subject_key`/`project_id` exactos (`None` cuenta como límite propio, no como comodín); una única decisión aprobada vigente prevalece de forma trazable (se devuelve la decisión misma); dos o más recuerdos vigentes sin una decisión que arbitre, o dos o más decisiones aprobadas del mismo límite (un estado ya inconsistente que la regla tampoco arbitra en silencio), producen un conflicto explícito con los elementos implicados; nunca se usa fecha, orden de inserción ni puntuación opaca como desempate.
- *Integración en la capa de aplicación:* `EvaluateMemoryPrecedenceUseCase`, de solo lectura (como `GetMemoryOriginUseCase`/`GetDecisionOriginUseCase`, sin `UnitOfWork`), reutiliza `MemoryRepository.list_current_memories()`/`DecisionRepository.list_current_decisions()` ya existentes — ningún método de repositorio ni tabla nueva más allá de los dos campos de `Memory`. `SendMessageUseCase` nunca lo llama, igual que con el resto de casos de uso de B4: una conversación ordinaria nunca crea, corrige, resuelve ni aprueba recuerdos o decisiones.
- *Conexión mínima en la construcción del contexto:* `ContextBuilder` gana un parámetro `decision_repository: DecisionRepository | None = None`, opcional y `None` por defecto — omitirlo deja `build()` idéntico byte a byte al comportamiento previo a B4e (los 11 puntos de construcción existentes en pruebas no necesitaron cambio alguno). Cuando `composition_root` lo inyecta (único punto de producción que lo hace), `build()` agrupa los recuerdos vigentes con `subject_key` no nulo por límite de asunto/proyecto y excluye del contexto ordinario únicamente los que quedan en conflicto sin resolver; un recuerdo sin `subject_key`, o ya resuelto por una decisión vigente, se incluye exactamente igual que antes. Ni las decisiones como sección propia del contexto ni la interfaz de conflicto (panel, pregunta de aclaración visible) forman parte de este corte — permanecen en B4f.
- *Pruebas:* Ruff, mypy y pytest en verde (884 pruebas: 830 previas + 54 nuevas), incluidas: los 8 casos mínimos obligatorios de la incidencia a nivel de dominio (conflicto explícito entre dos recuerdos incompatibles; precedencia trazable de una decisión aprobada vigente; ausencia de precedencia desde una decisión `PROPOSED`/`SUPERSEDED`/`ARCHIVED`; exclusión de recuerdos `ARCHIVED`/`DELETED`; ausencia de colisión entre asuntos o proyectos distintos, incluida la distinción entre `project_id=None` como límite propio y como comodín; ausencia de desempate por fecha o inserción; migración sin pérdida; una conversación ordinaria no resuelve nada); caso de uso de aplicación con fakes; wiring de composición con SQLite real de extremo a extremo (conflicto, precedencia, exclusión del contexto assemblado); migración Alembic real (`upgrade`/`downgrade`, columna física con FK, preservación de datos previos); y regresión completa de RF-019 a RF-025 y PA-010 a PA-016 de B4a–B4d.

Una PR quedó abierta hacia `main`, pendiente de revisión y sin merge. B4f sigue sin iniciarse.