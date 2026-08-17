# V8 — Ejecución, puertas y evidencia

Este documento es el registro operativo único de V8. No sustituye el Producto, el Plan de Pruebas, la Arquitectura, las ATD ni `docs/implementation/PLAN.md`.

Por ADR-005, es además el **único sitio del repositorio donde se declara el
estado** de un bloque de V8 o de un defecto del catálogo. `PLAN.md` describe el
plan; `REPOSITORY_STATUS.md` describe qué hay construido; ninguno de los dos
dice en qué punto está. Si un documento contradice a este en materia de estado,
manda este.

## Estado

- V8.1 — Corrección documental y automatizada: **ACTIVA**.
- V8.2 — Windows sin clave: **BLOQUEADA** hasta integración automática verde.
- V8.3 — Proveedor real: **BLOQUEADA**.
- V8.4 — PA-E2E-01 y cierre: **BLOQUEADA**.
- Sirius 0.1: **NO ACEPTADO** y **NO TERMINADO**.

**V8.1 no tiene ya trabajo automatizable pendiente.** B1 a B12 están completos
en su parte automatizable y B13 está cerrado por declaración del propietario,
con la salvedad escrita en su fila. Lo que bloquea V8.2 y V8.3 no es código:
es Windows real y una clave real, y ambas cosas exigen al propietario.

**B12e cierra el riesgo que B12c destapó** (ADR-008): `list_current_memories()`,
`list_archived_memories()`, `list_current_decisions()` y
`list_archived_decisions()` cargan ahora la revisión vigente del conjunto en
una sola consulta en vez de una por elemento. Construir el contexto pasa de
usar entre el 89 % y el 100 % de los 300 ms de RNF-003 a usar el 40 %. Ver la
sección de rendimiento y ADR-008.

No se crea una fase canónica adicional denominada `Preparación V8`.

## Fuentes normativas

- `docs/canonical/STATUS.md`
- Definición de Producto Sirius 0.1 aprobada
- Plan de Pruebas y Trazabilidad aprobado
- Arquitectura Técnica Sirius 0.1 aprobada
- ATD-001 a ATD-012
- `docs/implementation/PLAN.md`
- `AGENTS.md`

Los resúmenes de este documento no son normativos. Ante contradicción, prevalecen las fuentes aprobadas.

## Reglas de ejecución

- No ampliar el alcance de Sirius 0.1.
- No cambiar Producto, Arquitectura o ATD sin propuesta y aprobación explícita.
- No usar ni obtener una clave API real hasta abrir formalmente V8.3.
- No introducir voz, robótica, web, archivos externos, herramientas, automatización, RAG, multiagente ni programación supervisada.
- Cada corrección debe enlazar con un requisito aprobado y una prueba identificada.
- Trabajar en ramas breves, con cambios pequeños, reversibles y comprobaciones verdes.
- No confundir infraestructura implementada, comportamiento utilizable, prueba automática, prueba manual y aceptación formal.

## Puertas

### Puerta V8.2 — Windows sin clave

Debe cumplirse:

- integración automática verde sobre el estado exacto que se probará;
- defectos funcionales del bloque correspondiente corregidos;
- ejecutable reproducible disponible cuando la prueba lo requiera;
- guion manual con resultados esperados;
- entorno de datos desechable y copia externa preparada.

### Puerta V8.3 — Proveedor real

Debe cumplirse todo lo anterior y además:

- D-01, D-02, D-03, D-04, D-05, D-08, D-11 y A-01 cerrados;
- D-06, D-07, D-09 y D-10 corregidos o resueltos conforme al Plan de Pruebas;
- A-02 y A-03 verificados;
- suite automática PA/SP sin clave completamente verde;
- Credential Manager comprobado con un valor señuelo;
- copia y restauración comprobadas desde el ejecutable;
- cero defectos bloqueantes o altos conocidos;
- autorización explícita del usuario para obtener y usar una clave temporal.

### Puerta V8.4 — E2E y cierre

Debe cumplirse:

- ventana de proveedor real completada sin defectos bloqueantes;
- PA-001 a PA-025 ejecutables;
- PS-01 a PS-07 preparados para evaluación humana;
- SP-01 a SP-07 ejecutables;
- entorno, versión, commit y artefacto identificados;
- proyecto pequeño de aceptación definido y no canónico.

## Catálogo cerrado de trabajo

Este catálogo **no declara estado**. Cada defecto lo cierra un bloque, y el
estado se lee en la tabla de bloques de la sección siguiente, que es la única
autoritativa (ADR-005). Tener el mismo hecho en dos tablas fue lo que las
dejó contradiciéndose entre sí.

| ID | Resumen | Fuente principal | Bloquea proveedor real | Bloquea cierre | Lo cierra |
|---|---|---|---:|---:|---|
| D-01 | Onboarding y validación de credencial | RF-001/002; PA-001/002 | Sí | Sí | B2 |
| D-02 | Proyecto operable | RF-014–018; PA-006–009 | Sí | Sí | B3 y B4 |
| D-03 | Eventos, memoria y decisiones | RF-019–026; PA-010–016 | Sí | Sí | B4 |
| D-04 | Panel de contexto | Producto §9.1 | Sí | Sí | B5 |
| D-05 | Reintento sin reescribir | RF-007; PA-003/017 | Sí | Sí | B7 |
| D-06 | Markdown seguro y código copiable | RF-008; SP-07 | No | Sí | B8 |
| D-07 | Exportación estructurada | RF-031; PA-020; ATD-009 | No | Sí | B9 |
| D-08 | Errores accionables | RF-028; RNF-018 | Sí | Sí | B7 |
| D-09 | Aviso de presupuesto | RF-030; PA-018 | No | Sí | B7 |
| D-10 | Ruta de datos y activación clara | Producto §5.1 | No | Sí | B2 y B14 |
| D-11 | Contexto pertinente y limitado | RNF-008; SP-03; ATD-007 | Sí | Sí | B6 |
| A-01 | Política de acciones fuera de alcance | RF-035; PA-024 | Sí | Sí | B10 |
| A-02 | Recuperación tras cierre forzado | RNF-005/006; PA-019 | No | Sí | B11 |
| A-03 | Empaquetado reproducible | ATD-011 | Sí, como puerta | Sí | B13 |
| A-04 | Evidencia de aceptación trazada | Plan de Pruebas | No, por sí sola | Sí | B12 y B16 |

Cualquier defecto nuevo debe vincularse a un requisito ya aprobado. Si no puede hacerse, debe detenerse el trabajo y solicitar decisión.

### Qué significa «cerrado» aquí

Un defecto **cerrado en su parte automatizable** tiene su comportamiento
implementado y cubierto por pruebas automáticas con dobles deterministas. No
significa que su prueba de aceptación formal esté superada: las PA que exigen
proveedor real, Windows real o evaluación humana permanecen sin declarar hasta
V8.3 y V8.4. Esta distinción es la que separa infraestructura de aceptación, y
no debe borrarse al resumir.

## Bloques operativos

**Esta tabla es el único registro autoritativo del estado de V8 (ADR-005).**
Ningún otro documento del repositorio declara el estado de un bloque o de un
defecto; `PLAN.md` y `REPOSITORY_STATUS.md` enlazan aquí. Un bloque que se
fusiona actualiza esta tabla y nada más.

| Bloque | Entrega | Estado |
|---|---|---|
| B1 | Reconciliación documental y trazabilidad | Completo (ADR-005: el estado de V8 vive solo en esta tabla; `PLAN.md` y `REPOSITORY_STATUS.md` dejan de copiarlo y `tests/unit/test_documentation_single_source.py` falla si vuelven a hacerlo) |
| B2 | Onboarding, credencial, ruta y activación | Completo en su parte automatizable (RF-001 y RF-002 implementados y cubiertos: `OnboardingWindow`, `ValidateAndSaveApiKeyUseCase`, `ValidatedMainWindow`; B2b resuelve, valida y persiste la ruta local antes de SQLite, logging y composición. D-01 cerrado en su parte automatizable; PA-001 y PA-002 exigen proveedor real (V8.3). D-10 **cerrado el 2026-08-10**: su única condición pendiente era la comprobación real en Windows, que pertenecía a B14, y B14 quedó completo ese día. PA-001 y PA-002 siguen exigiendo proveedor real) |
| B3 | Proyecto mínimo y ciclo de vida | Completo (B3a, B3b y B3c implementados y cubiertos automáticamente: saludo inicial y primer proyecto utilizable, continuidad observable —estado, bloqueos, siguiente paso, resumen al retomar— y ciclo de vida versionado con `project_revisions` inmutables; RF-014 a RF-018 cubiertos. D-02 cerrado en su parte automatizable junto con B4; PA-008 y PA-009 exigen decisión registrada evaluada con proveedor real) |
| B4 | Eventos, recuerdos, decisiones y conflictos | Completo (B4a a B4f fusionados en `main`: guardado manual con origen consultable, decisiones con aprobación explícita, corrección versionada y sustitución, archivo/eliminación con redacción de origen, precedencia y detección determinista de conflictos, y la pestaña «Memoria y decisiones» que lo integra con `GetKnowledgeOverviewUseCase`. RF-019 a RF-026 y PA-010 a PA-016 cubiertos automáticamente con proveedor simulado; D-03 cerrado en su parte automatizable) |
| B5 | Panel de contexto | Completo (PR #79, squash `7370a19`, incidencia #60: `ContextPanelWidget` integra en la pestaña «Conversación» un panel de solo lectura con el proyecto activo y su siguiente paso, las decisiones APPROVED vigentes y los recuerdos vigentes, con consulta de origen y actualización local bajo demanda; sin repositorios, modelos, migraciones ni red nuevos. D-04 cerrado) |
| B6 | Selección y presupuesto de contexto | Completo (B6a, B6b, B6c y B6d implementados y cubiertos automáticamente: índices FTS5, su sincronización transaccional, recuperación/ordenación de relevancia comprobable, presupuesto/recorte determinista con `TokenCounter` estimador local, y su cableado dentro de `ContextBuilder` con la sección de decisiones vigentes relacionadas; D-11 cerrado) |
| B7 | Reintento, errores y presupuesto | Completo (B7a, B7b y B7c implementados y cubiertos automáticamente: mapeo `LLMErrorKind` -> mensaje accionable, "Reintentar" para un envío `FAILED`/crasheado que reenvía el mismo texto con un `operation_id` nuevo sin reescribir, y aviso no bloqueante al acercarse al límite mensual de presupuesto (`GetBudgetStatusUseCase`); D-05, D-08 y D-09 cerrados en su parte automatizable; B7 completo) |
| B8 | Markdown seguro y copia de código | Completo (B8a y B8b implementados y cubiertos automáticamente: mensajes renderizados como Markdown seguro con el motor nativo de Qt, sin HTML activo, y cada bloque de código cercado con su propio botón "Copiar" que coloca el código exacto en el portapapeles; D-06 cerrado en su parte automatizable) |
| B9 | Exportación estructurada | Completo (B9a y B9b implementados y cubiertos automáticamente: `ExportService`/`ExportStructuredUseCase` y la acción "Exportar" en la interfaz, con aviso previo y ejecución en segundo plano; D-07 cerrado) |
| B10 | Política de acciones fuera de alcance | Completo (política RF-035 añadida a la semilla canónica de identidad y renderizada en las instrucciones; A-01 cerrado en su parte automatizable) |
| B11 | Recuperación tras cierre forzado | Completo (prueba de integración que simula un cierre forzado —repositorios abandonados sin `close()` ordenado— sobre SQLite real migrado con Alembic, demostrando que el estado confirmado sobrevive íntegro, `PRAGMA integrity_check` es `ok`, un turno interrumpido a mitad de streaming deja el historial coherente sin fila parcial, y la reapertura es idempotente; `PRAGMA synchronous=FULL` afirma la durabilidad explícitamente; A-02 cerrado en su parte automatizable) |
| B12 | Suite PA/SP automática, rendimiento y evidencia | Completo en su parte automatizable. **B12a** (ADR-006): `docs/implementation/TRAZABILIDAD_PA_SP.md` enlaza los 40 identificadores del Plan de Pruebas con las pruebas que cubren su parte automatizable, y `tests/unit/test_pa_sp_traceability.py` comprueba por máquina que cada prueba nombrada exista. El hueco era de trazabilidad, no de cobertura: 28 de 40 no se citaban en ninguna prueba, pero el comportamiento sí estaba probado. **B12c completo** (ADR-007): `tests/integration/test_local_performance.py` mide P50/P95 sobre el conjunto de referencia del plan (5.000 mensajes, 500 recuerdos, 100 decisiones, 10 proyectos; 30 repeticiones), afirma el límite aprobado donde hay un orden de magnitud de holgura —inicio, 30 ms frente a 3.000— y vigila el resto con un guardarraíl declarado. **Destapó un riesgo de producto: construir el contexto consume entre el 89 % y el 100 % de sus 300 ms**, por 501 consultas para 500 recuerdos en `list_current_memories()`; corregirlo es código productivo y espera decisión. **B12d completo**: evidencia consolidada en el registro de este archivo. B12b queda sin contenido: tras B12a el único hueco automatizable era PA-025, que cierra B12c. **B12e completo** (ADR-008, corte correctivo sobre lo que B12c midió, incidencia #148): `SqliteMemoryRepository.list_current_memories()`/`list_archived_memories()` y `SqliteDecisionRepository.list_current_decisions()`/`list_archived_decisions()` cargan la revisión vigente del conjunto en una única consulta `IN (...)` en vez de una por elemento, sin cambiar qué devuelven. `tests/integration/test_memory_decision_list_query_count.py` fija por prueba que el número de consultas de los cuatro métodos no crece con el número de elementos, verificada por mutación. Construir el contexto baja de 239,8 ms a 120,9 ms P95 sobre el mismo conjunto de referencia y la misma máquina; PA-025 sigue sin declararse superada |
| B13 | Empaquetado reproducible | Completo **por declaración del propietario** el 10 de agosto de 2026: declara ejecutados los builds de Windows que faltaban. Implementado y cubierto: el proceso de empaquetado, los scripts de build y verificación y `_resource_root`, que resuelve `alembic.ini`/`migrations/` junto al ejecutable cuando la app corre congelada (PyInstaller `sys.frozen` o Nuitka `__compiled__`) y desde la raíz en desarrollo. **Sin evidencia escrita en el repositorio**: no hay salida de build ni de verify adjunta, así que A-03 —que es puerta de V8.3— queda cerrado sobre la palabra del propietario y no sobre una comprobación registrada. La PR #122 sigue abierta. Ver la nota de A-03 en el registro de evidencia |
| B14 | Windows sin clave | Completo **por declaracion del propietario** el 10 de agosto de 2026. Las 9 partidas cerradas: ejecutable Nuitka (via B13); trafico sin proveedor real (`scripts/verify_windows_no_network.ps1`, 45 muestras del arbol de procesos y ninguna conexion saliente); **Credential Manager con valor senuelo, ejecutado por el propietario**; rutas y funcionamiento sin administrador, e inspeccion de archivos, logs, copias y exportaciones (via la verificacion de B13); escalado, teclado y foco (`tests/gui`); cierre forzado (`test_forced_shutdown_recovery.py`, y **PA-019 manual ejecutada por el propietario** sobre el paquete); restauracion (8 pruebas de copia y restauracion); y rendimiento local (B12c, ADR-007). Marcador y evidencia en `docs/implementation/B14_WINDOWS_SIN_CLAVE.md` |
| B15 | Ventana compacta con proveedor real | Completo **por declaración del propietario** el 2026-08-10. Ejecutada con clave y proveedor reales: PA-001 (clave válida valida, protege y abre la conversación), PA-002 (clave inválida rechazada, explicada y no guardada), PA-008 (decisiones y bloqueos recuperados al volver dias despues, decisiones aun vigentes), PA-009 (la recomendacion del siguiente paso cuadra con el estado real del proyecto) y PA-023 (trafico solo hacia el proveedor configurado) |
| B16 | PA-E2E-01, regresión y cierre | Completo **por declaración del propietario** el 2026-08-10. PA-E2E-01 ejecutada sobre un proyecto real durante varias sesiones; PS-01 a PS-07 evaluadas por el propietario como juicio global. La suite automatica completa quedo en verde el mismo dia (2285 pruebas, 0 fallos) |

## Criterio de cierre de bloque

Un bloque solo puede marcarse terminado cuando:

- el alcance está trazado a requisitos aprobados;
- las pruebas previstas existen y pasan;
- `scripts/check.ps1` pasa cuando el bloque contiene código;
- CI está verde en la PR;
- no quedan comentarios de revisión sin resolver;
- la documentación operativa refleja el comportamiento real;
- el usuario autoriza el merge.

## Registro de evidencia

Añadir una fila por resultado verificable. No registrar secretos ni contenido sensible.

| Fecha | Bloque | Commit/artefacto | Tipo | Prueba | Resultado | Evidencia | Observaciones |
|---|---|---|---|---|---|---|---|
| 2026-07-15 | B1 | `a05af3c` | Documental | Reconciliación de estado y puertas | Superada | PR #17, CI Quality verde | Sin cambios funcionales |
| 2026-07-16 | B2 | `fcba319` (PR #19) | automática | `test_validate_and_save_api_key.py`, `test_openai_credential_validator.py`, `test_composition_root_credential_validation.py` | Superada | CI verde, `scripts/check.ps1` verde | RF-002 está implementado y cubierto automáticamente (caso de uso y validador contra el proveedor, sin GUI todavía). D-01 permanece abierto hasta demostrar el resto de sus condiciones |
| 2026-07-16 | B2 | `fba51df` (PR #20) | automática | `test_validated_main_window.py` | Superada | CI verde, `scripts/check.ps1` verde | Integra RF-002 en la GUI (`ValidatedMainWindow`). D-01 permanece abierto: falta RF-001 (pantalla de primera configuración con política de datos); D-10 permanece abierto sin ningún cambio; PA-001 y PA-002 no se declaran superadas — exigen credencial real y quedan bloqueadas hasta V8.3 |
| 2026-07-17 | B2a | `f7134ca` (PR #24) | automática | `test_onboarding_window.py`, `test_app_bootstrap.py`, `test_composition_root_credential_validation.py` (nuevos casos), `test_send_message.py` (`set_llm_provider`), suite GUI de B2a repetida 5 veces | Superada | CI verde, `scripts/check.ps1` verde localmente (Ruff format, Ruff lint, mypy estricto, 360 pytest) | RF-001 implementado y cubierto automáticamente vía `OnboardingWindow` + recomposición segura del proveedor en la misma ejecución (`activate_configured_llm_provider`, sin reinicio). D-01 permanece abierto hasta PA-001/PA-002 con proveedor real; D-10 sigue parcialmente abierto (falta B2b y la comprobación real de Credential Manager); sin clave real ni red |
| 2026-07-16 | B1 | `0f5af4e` (PR #22) | automática | `tests/gui/test_backup_recovery_ui.py` (23/23, 5 repeticiones) | Superada | CI verde, `scripts/check.ps1` verde | Corrección de higiene de prueba (fuga de conexión SQLite en el helper de bootstrap), no defecto de producto; sin cambio de comportamiento aprobado de V7 |
| 2026-07-17 | B2b | `2c60afc` (PR #26) | automática | `test_paths.py`, `test_data_path_validator.py`, `test_bootstrap_location_store.py`, `test_data_location_use_case.py`, `test_data_location_window.py`, `test_app_bootstrap.py`; suite GUI de B2b repetida 5 veces | Superada | CI verde, `scripts/check.ps1` verde localmente (Ruff format, Ruff lint, mypy estricto, 412 pytest) | Selección y persistencia de la ruta local de datos antes de SQLite, logging y composición (D-10, parte de B2). Sin clave real ni red; sin movimiento ni migración de datos existentes |
| 2026-07-17 | B3a | `882ab62` (PR #27) | automática | `test_project_domain.py` (nuevos casos), `test_initial_project_use_case.py` (unit e integración), `test_initial_project_window.py`, `test_app_bootstrap.py` (nuevos casos); suite GUI de B2a/B2b/B3a repetida 5 veces | Superada | CI verde, `scripts/check.ps1` verde localmente (Ruff format, Ruff lint, mypy estricto, 455 pytest) | Saludo determinista y creación utilizable del primer proyecto (D-02, parcial). RF-014 cubierto automáticamente; RF-015 protegido en la capa de aplicación; parte inicial de RF-016 (estado y siguiente paso iniciales) cubierta. Sin clave real ni red; sin B3b, B4 ni B5 |
| 2026-07-17 | B3b | `a2f74df` (PR #28) | automática | `test_project_domain.py` (nuevos casos), `test_project_continuity_use_case.py`, `test_render_instructions.py`, `test_sqlite_project_repository.py` (nuevos casos), `test_migrations.py` (nuevos casos, Alembic real), `test_send_message.py` (nuevo caso), `test_composition_root_project_continuity.py`, `test_project_continuity_widget.py`, `test_main_window.py` (nuevos casos), `test_app_bootstrap.py` (nuevos casos); suite GUI de B2a/B2b/B3a/B3b repetida 5 veces | Superada | `scripts/check.ps1` verde localmente (Ruff format, Ruff lint, mypy estricto, 518 pytest) | Continuidad observable del proyecto activo (D-02, parcial). RF-016 cubierto en estado, bloqueos y siguiente paso (no en decisiones, que pertenecen a B4); RF-017 cubierto (recuperación y resumen breve al retomar). Migración Alembic no destructiva (`66951344e4b9`) probada con Alembic real desde el head anterior. Sin clave real ni red; sin completar/archivar, B4, B5 ni B6 |
| 2026-07-18 | B1 | PR #33, PR #34 (`e4a19a9`) | documental | Prueba de humo cloud (`docs/implementation/CLOUD_SMOKE_TEST.md`) | Superada | `CLOUD_SMOKE_PASSED`; evidencia en `docs/implementation/CLOUD_SMOKE_EVIDENCE_20260718.md`; PR #33 corrigió el aislamiento multiplataforma de las pruebas; PR #34 fusionó la evidencia | Ruff format, Ruff lint y mypy correctos; 562 pruebas superadas (`uv run pytest`); ejecución remota sin depender del ordenador del usuario; sin merge automático; no cierra B4 ni D-03; Sirius 0.1 sigue NO ACEPTADO y NO TERMINADO |
| 2026-07-18 | B3c | PR #29 | automática | `test_project_domain.py`, `test_render_instructions.py` (reescritos para el nuevo dominio con revisión, incluida la sección de proyecto ausente); `test_initial_project_use_case.py`, `test_project_continuity_use_case.py` (reescritos sobre `create_project`/`append_revision`); `test_project_lifecycle_use_case.py` (nuevo); `test_sqlite_project_repository.py` (reescrito: `ensure_bootstrap_project`, `create_project`, `append_revision`, `complete_active_project`, `list_project_revisions`, JSON de bloqueos corrupto, puntero `current_revision_id`, revisión de otro proyecto rechazada, rollback ante fallo entre inserción y actualización del puntero); `test_migrations.py` (nuevos casos: backfill a revisión 1 con `current_revision_id` fijado, placeholder sin revisión con puntero `NULL`, fila inactiva histórica como COMPLETED, downgrade con resincronización de columnas heredadas vía el puntero, FK física `current_revision_id → project_revisions.id`, Alembic real); `test_initial_project_persistence.py`, `test_send_message.py`, `test_persistence_bootstrap.py`, `test_secret_leakage.py` (adaptados a la nueva forma del proyecto); `test_context_builder.py` (reescrito: cero proyectos activos, solo placeholder y proyecto COMPLETED ya no fallan y devuelven `context.project=None`); `test_backup_restore_project_lifecycle.py` (nuevo: copia/restauración conservan proyectos, revisiones, punteros `current_revision_id`, el único proyecto activo, y `ContextBuilder` usa el proyecto restaurado correcto); `test_project_continuity_widget.py` (nuevos casos "Completar proyecto"), `test_initial_project_window.py`, `test_main_window.py`, `test_app_bootstrap.py`, `test_settings_ui.py`, `test_validated_main_window.py`, `test_backup_recovery_ui.py`, `test_conversation_ui.py`, `test_onboarding_window.py` (adaptados a la nueva firma de `MainWindow`/`ProjectRepository`); suite GUI completa repetida 5 veces | Superada | `scripts/check.ps1` verde localmente (Ruff format, Ruff lint, mypy estricto, 557 pytest) | Ciclo de vida y versionado del proyecto (D-02, parcial). RF-018 cubierto: completar el proyecto activo (`ProjectLifecycleUseCase`) sin borrar su historial, con confirmación explícita en `ProjectContinuityWidget` ("Completar proyecto") y transición en el mismo proceso a `InitialProjectWindow` (nunca reactiva ni sobrescribe el proyecto cerrado). Historial de continuidad versionado e inmutable (`project_revisions`) con `projects.current_revision_id` (SIRIUS-ARQ-0.1 S7.3, campo mínimo aprobado) como único puntero autoritativo a la revisión vigente — corregido en auditoría de cierre tras detectarse que la primera implementación usaba en su lugar un indicador `is_current` no autorizado por la arquitectura — vía migración Alembic no destructiva (`6f710ea6c2d2`) con relleno (`backfill`) de la fila existente en revisión 1 y resincronización de columnas heredadas al bajar de versión. `ContextBuilder` ya no exige un proyecto activo: `Context.project` es `Project \| None` (SIRIUS-ARQ-0.1 S3, `LLMRequest.project_context: str \| None`), y su ausencia nunca lanza `ContextAssemblyError`. Solo se implementa COMPLETED (RF-018 no menciona archivar; ARCHIVED queda fuera de alcance de Sirius 0.1). Sin clave real ni red; sin decisiones, eventos, B4, B5 ni B6 |
| 2026-07-18 | B4a | PR #36 (`c025683`) | automática | `test_manual_memory_origin.py`, `test_save_manual_memory_use_case.py`, `test_save_manual_memory_unit_of_work.py`, `test_composition_root_manual_memory.py`, `test_migrations.py` (eventos y enlace de origen) | Superada | CI `Quality` verde, `scripts/check.ps1` verde localmente (602 pytest) | Origen consultable y guardado manual de recuerdos (RF-019, RF-021, PA-010). Evento de origen persistente, enlace real recuerdo-evento-mensaje, `UnitOfWork` compartida (corregido en la misma PR tras un `BLOCKER` transaccional de Fase C). Sin decisiones, sustitución, B4c, B4d, B4e ni B4f |
| 2026-07-18 | B4b | PR #37 (`d1bbb87`) | automática | `test_decision_domain.py`, `test_propose_decision_use_case.py`, `test_approve_decision_use_case.py`, `test_decision_origin_use_case.py`, `test_decision_lifecycle.py`, `test_decision_unit_of_work.py`, `test_sqlite_decision_repository.py`, `test_composition_root_decisions.py`, `test_migrations.py` (decisiones) | Superada | CI `Quality` verde, `scripts/check.ps1` verde localmente (669 pytest) | Decisiones y aprobación explícita (RF-020, PA-011). `Decision`/`DecisionRevision` con estados PROPOSED/APPROVED, aprobación con confirmación explícita obligatoria, ninguna exploración conversacional crea ni aprueba una decisión. Sin sustitución, corrección, B4c, B4d, B4e ni B4f. **PR #37 fusionada en `main`** el 18 de julio de 2026 (verificado sobre `origin/main` antes de iniciar B4c) |
| 2026-07-18 | B4c | PR #39 (`e244649`) | automática | `test_correct_memory_use_case.py`, `test_correct_memory_unit_of_work.py`, `test_memory_correction_lifecycle.py`, `test_supersede_decision_use_case.py`, `test_decision_domain.py` (nuevos casos `ensure_can_supersede`), `test_decision_unit_of_work.py` (nuevos casos de sustitución), `test_sqlite_decision_repository.py` (nuevos casos de sustitución/consulta vigente), `test_decision_lifecycle.py` (nuevos casos E2E de sustitución), `test_send_message.py` (dos nuevos casos negativos: ninguna corrección ni sustitución automática), `test_composition_root_manual_memory.py`/`test_composition_root_decisions.py` (nuevos casos de wiring), `test_migrations.py` (nuevos casos de la migración `05559a954593`) | Superada | Ruff format, Ruff lint y mypy estricto correctos; 735 pytest (669 previas + 66 nuevas); `git diff --check` y `git status --short` limpios | Corrección y sustitución (RF-022, RF-023, PA-012, PA-013). `CorrectMemoryUseCase` consolida la corrección ya existente desde V4 bajo el contrato transaccional de B4a (evento + nueva revisión inmutable + puntero vigente en una sola `UnitOfWork`). `DecisionStatus.SUPERSEDED`/`Decision.supersedes_decision_id` y `SupersedeDecisionUseCase` (confirmación explícita obligatoria, aprueba la sustituta y marca la sustituida como histórica en la misma transacción); `list_current_decisions()`/`get_superseding_decision()` para distinguir vigente de sustituida. Migración Alembic aditiva `05559a954593`. Sin clave real ni red; sin B4d, B4e ni B4f. **PR #39 fusionada en `main`** el 19 de julio de 2026 (commit `e244649affd11e6e1bdb8179adb00d2b6d610f7e`, CI `quality` verde), verificado directamente sobre `origin/main` antes de iniciar B4d |
| 2026-07-19 | B4d | PR borrador (rama `feat/b4d-archive-delete-redaction-20260719-01`) | automática | `test_archive_memory_use_case.py`, `test_archive_decision_use_case.py`, `test_delete_memory_use_case.py` (unit); `test_archive_memory_unit_of_work.py`, `test_archive_decision_unit_of_work.py`, `test_delete_memory_unit_of_work.py` (atomicidad/rollback con SQLite real); `test_memory_archive_delete_lifecycle.py`, `test_decision_archive_lifecycle.py` (E2E); `test_sqlite_memory_repository.py`/`test_sqlite_decision_repository.py`/`test_sqlite_conversation_repository.py` (nuevos casos de archivo/eliminación/redacción); `test_composition_root_archive_delete.py` (wiring); `test_send_message.py` (dos nuevos casos negativos: ninguna conversación ordinaria archiva ni elimina); `test_decision_domain.py`/`test_conversation_domain.py` (nuevos casos de dominio); `test_migrations.py` (nuevos casos de la migración `bf0ac43b986b`) | Superada | Ruff format, Ruff lint y mypy estricto correctos; 830 pytest (735 previas + 95 nuevas); `git diff --check` y `git status --short` limpios | Archivo, eliminación y redacción de origen (RF-024, RF-025, PA-015, PA-016, SP-06). `ArchiveMemoryUseCase`/`ArchiveDecisionUseCase` consolidan el archivo ya implementado a nivel de repositorio desde V4 (memoria) y añaden el estado `DecisionStatus.ARCHIVED` (decisión, solo alcanzable desde APROBADA) bajo el contrato transaccional de B4a/c (evento + cambio de estado en una sola `UnitOfWork`); `MemoryRepository.list_archived_memories()`/`DecisionRepository.list_archived_decisions()` son las consultas explícitas de archivados. `DeleteMemoryUseCase` exige `confirmed=True` y una elección explícita y tipada (`SourceMessageChoice.PRESERVE`/`REDACT`, sin valor por defecto) antes de abrir transacción alguna; reutiliza `MemoryRepository.delete_memory()` (V4, ya redacta el contenido estructurado de toda la historia de revisiones conservando el marcador mínimo: id, versión, origen, fecha) y añade `ConversationRepository.redact_message()` (nuevo, migración `bf0ac43b986b`: `messages.content` pasa a nulo y `messages.redacted_at` se añade, mismo patrón NOT NULL→nullable en modo por lotes que `f5fb28ed426a`) para el mensaje fuente, dentro de la misma transacción que el evento y el borrado de contenido — un fallo en cualquier paso revierte los tres. La eliminación de decisiones queda deliberadamente fuera de esta implementación: ni PA-016 ni la enumeración de estados de decisión de Producto S6 la mencionan (a diferencia de "archivada", que sí aparece explícitamente), así que solo `Memory` es eliminable en este corte. `DeleteMemoryUseCase.delete()` devuelve también la advertencia aprobada sobre copias antiguas (SP-06/DR-012). Sin clave real ni red; sin B4e ni B4f; sin merge; sin incidencia `agent-review-requested` (no autorizada para este corte) |
| 2026-07-19 | B4e | PR #52 (fusionada) | automática | `test_precedence_domain.py`, `test_composition_root_precedence.py`, `test_sqlite_memory_repository.py`/`test_context_builder.py` (nuevos casos), `test_migrations.py` (migración `94418c79da9d`) | Superada | Ruff format, Ruff lint y mypy estricto correctos; 873 pytest (830 previas + 43 nuevas). Corrección 2026-08-14: la fila citaba una prueba de nombre test_detect_precedence_conflicts_use_case (sin acentos graves a propósito: entre ellos volvería a leerse como evidencia) que nunca existió en el repositorio; el caso de uso lo cubre `test_composition_root_precedence.py` | Precedencia y conflictos (RF-026, PA-014, DR-011). `Memory.subject_key`/`Memory.project_id` (opcionales, mirroring `Decision`); `sirius.domain.precedence.evaluate_subject_precedence`/`find_subject_conflicts`, determinista, sin desempate por fecha ni orden; `DetectPrecedenceConflictsUseCase` de solo lectura; conexión mínima en `ContextBuilder` que excluye únicamente el recuerdo ya superado por una decisión `APPROVED` inequívoca del mismo asunto, sin tocar un conflicto genuino. Sin clave real ni red; sin B4f. **PR #52 fusionada en `main`** el 20 de julio de 2026 (verificado sobre `origin/main` antes de iniciar B4f) — fila añadida en auditoría de cierre de B4f, dado que no se había registrado en su momento |
| 2026-07-20 | B4f | rama `claude/focused-bohr-3dj9el`, PR pendiente | automática | `test_composition_root_knowledge_overview.py` (nuevo); `test_sqlite_decision_repository.py` (nuevo caso `list_proposed_decisions`); `test_knowledge_widget.py` (GUI, nuevo: guardar/corregir/archivar/eliminar recuerdo con ambas elecciones y advertencia, proponer/aprobar/sustituir/archivar decisión, consultar origen de ambos, detectar conflictos con y sin conflicto pendiente, coordinación de estado ocupado, con los doce casos de uso reales de `composition_root` contra SQLite temporal); `test_main_window.py`/`test_conversation_ui.py`/`test_settings_ui.py`/`test_backup_recovery_ui.py`/`test_validated_main_window.py` (adaptados a la pestaña nueva y a la firma ampliada de `MainWindow`/`ValidatedMainWindow`) | Superada | Ruff format, Ruff lint y mypy estricto correctos; 928 pytest (873 previas + 55 nuevas); `git diff --check` limpio | Integración observable y cierre de B4 (PA-010 a PA-016 completas en su parte automatizable). `KnowledgeWidget` (pestaña nueva "Memoria y decisiones" de la misma `MainWindow`, sin aplicación de gestión independiente) integra, mediante los doce casos de uso ya existentes de B4a-B4e sin duplicar lógica de dominio: guardar/corregir/archivar/eliminar recuerdos (con la elección explícita de conservar o redactar el mensaje fuente y la advertencia sobre copias antiguas, SP-06/DR-012); proponer/aprobar/sustituir/archivar decisiones; consultar el origen de ambos; y mostrar los conflictos de precedencia de B4e sin resolverlos ni elegir en silencio. Nueva consulta de solo lectura `GetKnowledgeOverviewUseCase` y método mínimo `DecisionRepository.list_proposed_decisions()` (indispensable para que una decisión propuesta sea descubrible y aprobable desde la interfaz). Sin clave real ni red; sin B5, B6 ni otro bloque; sin merge |
| 2026-07-21 | B6a | rama `feature/b6a-fts5-sync-20260721-01`, PR pendiente | automática | `test_fts5_availability.py` (nuevo: confirma FTS5 compilado en el SQLite del entorno, vía `sqlite3` y vía el motor SQLAlchemy de Sirius); `test_migrations.py` (nuevos casos: `message_fts`/`knowledge_fts` creadas al llegar a `head`, downgrade que elimina solo esos índices y sus triggers dejando datos base intactos, backfill de un mensaje y de una revisión vigente de memoria/decisión ya existentes antes de esta migración, con la revisión histórica no vigente excluida del backfill); `test_search_index_sync.py` (nuevo, contra SQLite real migrado con Alembic: alta de mensaje/recuerdo/decisión indexa en la misma transacción, corrección de recuerdo reemplaza el texto indexado, archivar recuerdo/decisión conserva el texto indexado, aprobar/archivar una decisión no lo toca, y las dos pruebas de la invariante crítica — redactar un mensaje y eliminar un recuerdo dejan de ser recuperables por FTS —, más una prueba de fallo en el commit que confirma que el dato y la entrada del índice se revierten juntos) | Superada | Ruff format, Ruff lint y mypy estricto correctos; 1021 pytest (1006 previas + 15 nuevas) | Sustrato de búsqueda local (SIRIUS-ARQ-0.1 S7.1/S8.1; ATD-004; D-11, parcial). Migración Alembic escrita a mano (`61be4bb269bf`) crea `message_fts` (FTS5 "external content" sobre `messages`, `content_rowid='id'`, sin copia duplicada del texto) y `knowledge_fts` (FTS5 autocontenida que cubre memorias y decisiones bajo el mismo agrupamiento "conocimiento" que ya usa `GetKnowledgeOverviewUseCase` de B4f, con rowid sintético `id*2`/`id*2+1` para no mezclar los dos espacios de id). La sincronización es enteramente vía triggers SQLite creados en la propia migración (`AFTER INSERT/UPDATE/DELETE`) — ningún repositorio ni caso de uso llama a nada nuevo — por lo que la actualización del índice ocurre siempre dentro de la misma transacción SQLite que el dato, exactamente como exige S8.1: un fallo antes del commit revierte el dato y la entrada del índice juntos. Cierra la deuda anotada en `delete_memory.py` desde B4d ("FTS5 out of scope"): `DeleteMemoryUseCase`/`ConversationRepository.redact_message` no cambiaron una sola línea y el índice queda igualmente sincronizado. Invariante crítica verificada: el contenido eliminado (`DeleteMemoryUseCase`) o redactado (`redact_message`) deja de ser recuperable por FTS de inmediato. No añade búsqueda, relevancia, orden, presupuesto ni recorte de contexto (eso es B6b/B6c), no toca `ContextBuilder` ni el ensamblado de contexto (B6d), y no usa embeddings ni recuperación semántica (§7.5 lo prohíbe). Sin dependencias nuevas (FTS5 es parte de SQLite); sin clave real ni red; sin merge |

| 2026-07-21 | B6b | rama `feature/b6b-relevance-ranking-20260721-01`, PR pendiente | automática | `test_relevance_domain.py` (nuevo: cada criterio de la tupla de ordenación probado por separado — asunto de decisión coincidente, proyecto activo, coincidencia FTS5, recencia —, invariante que impide construir un recuerdo con coincidencia de asunto, desempate estable/determinista por el id sintético de `knowledge_fts`, y los dos filtros — no vigente y no relacionado — probados como exclusión, nunca como resta); `test_rank_relevant_knowledge.py` (nuevo, contra SQLite real migrado con Alembic y los casos de uso reales de B4/B6a, sin fakes de repositorio: solo conocimiento vigente vuelve — propuesta, sustituida y archivada quedan fuera igual que un recuerdo archivado o eliminado —, cada criterio de la tupla probado extremo a extremo, una prueba que demuestra que la coincidencia proviene del índice FTS5 real y no de un filtro Python (el tokenizador de FTS5 nunca coincide con una subcadena de un token, a diferencia de un `in` de Python), consulta vacía y con caracteres especiales sin excepción) | Superada | Ruff format, Ruff lint y mypy estricto correctos; 1055 pytest (1021 previas + 34 nuevas) | Recuperación de conocimiento vigente con relevancia simple y comprobable (SIRIUS-ARQ-0.1 S7.5; D-11, parcial). `sirius.domain.relevance.rank_relevant_knowledge` ordena por la tupla explícita que fija S7.5, sin fórmula opaca: decisión APROBADA vigente de asunto coincidente, proyecto activo, coincidencia FTS5, recencia — cada criterio booleano/entero e inspeccionable —, con desempate final estable por el mismo id sintético que `knowledge_fts` ya usa (`memory_id*2`/`decision_id*2+1`, B6a). Los dos términos negativos de S7.5 ("elemento general no relacionado", "estado histórico") se excluyen por filtro antes de ordenar, nunca se restan, y el propio dominio los re-verifica en vez de confiar en el llamador (mismo patrón que `sirius.domain.precedence`). `RankRelevantKnowledgeUseCase` (nuevo, solo lectura) combina los filtros estructurados (proyecto activo, asunto de decisión por contención de subcadena, sin similitud ni embeddings) con `KnowledgeSearchRepository`/`SqliteKnowledgeSearchRepository` (nuevo), que ejecuta un `MATCH` FTS5 real contra `knowledge_fts` y sanea el texto de consulta (`sanitize_fts5_query`: solo tokens alfanuméricos, cada uno citado literalmente y unidos con `OR`) para que ningún carácter especial rompa la sintaxis y una consulta vacía o solo puntuación nunca llegue a ejecutar un `MATCH` — devuelve sin coincidencias en vez de fallar. No se conecta a `ContextBuilder` ni al ensamblado de contexto (B6d), no aplica presupuesto ni recorte de nº de recuerdos (B6c), no usa mensajes recientes/`message_fts` (B6c/B6d) y no usa embeddings ni recuperación semántica (§7.5 lo prohíbe expresamente). Sin dependencias nuevas; sin clave real ni red; sin merge |

| 2026-07-21 | B6c | rama `feature/b6c-context-budget-trim-20260721-01`, PR pendiente | automática | `test_token_counter.py` (nuevo: texto vacío cuesta cero tokens, la estimación redondea hacia arriba desde cuatro caracteres por token con casos exactos en el borde, determinismo entre llamadas repetidas, un texto más largo nunca cuesta menos que un prefijo suyo); `test_context_budget.py` (nuevo, con un `TokenCounter` controlado — un token por carácter — para que toda la aritmética sea exacta: los valores por defecto son los aprobados (12000 tokens, 12 recuerdos/decisiones); presupuesto amplio deja todo intacto; el tope de 12 descarta primero los de menor relevancia según el orden ya fijado por B6b (incluido el caso de tope 0); el recorte por presupuesto de tokens descarta primero un recuerdo general aunque sea más relevante que una decisión, y solo agota los recuerdos antes de tocar cualquier decisión, incluso con varios recuerdos de por medio; los mensajes recientes llenan el presupuesto restante descartando primero los más antiguos; un mensaje-fuente (resuelto vía `source_event_id` -> `Event.message_id`, nunca a través de un repositorio) sobrevive a un mensaje no-fuente más reciente mientras quede alguno no-fuente que recortar, y se descarta él mismo en cuanto no queda ninguno; un presupuesto minúsculo nunca lanza excepción y dejar vacías tanto el conocimiento como los mensajes en vez de invadir las secciones protegidas; `protected_tokens`/`token_budget` negativos lanzan `ValueError`; un mensaje `CANCELLED`/`FAILED`/`REDACTED` nunca se selecciona aunque sobre presupuesto, re-verificado por el propio módulo en vez de confiar en el llamador; entrada vacía no selecciona nada) | Superada | Ruff format, Ruff lint y mypy estricto correctos; 1080 pytest (1055 previas + 25 nuevas) | Presupuesto y recorte de contexto deterministas y aislados (SIRIUS-ARQ-0.1 S6.2 "Límite de tokens"/S6.3 "Reglas de recorte"; D-11, parcial; ATD-007). Puerto nuevo `sirius.ports.token_counter.TokenCounter` con una única operación (`count_tokens`) y su implementación `CharacterHeuristicTokenCounter` (nueva, `sirius.adapters.llm`): heurística documentada de ~4 caracteres por token redondeando hacia arriba, sin `tiktoken` ni ninguna otra dependencia nueva, sin llamada al proveedor — el presupuesto es "una barrera con margen", no un conteo exacto. `sirius.application.context_budget.apply_context_budget` (nuevo, función pura sin puertos de repositorio) recibe el coste ya calculado de las secciones protegidas fijas (identidad, reglas/permisos, mensaje actual — nunca forman parte de la selección ni se recortan aquí), el conocimiento ya ordenado por B6b (`RankedKnowledge`, reutilizado sin reimplementar relevancia) y los mensajes recientes completos, con los valores por defecto aprobados (`token_budget=12000`, `max_knowledge_items=12`) como argumentos. Aplica primero el tope de 12 respetando el orden de B6b, después recorta por presupuesto de tokens descartando recuerdos generales antes que decisiones vigentes (nunca al revés), y finalmente llena el resto del presupuesto con los mensajes recientes descartando los más antiguos primero — salvo el mensaje-fuente (`source_event_id` -> `Event.message_id`, resuelto a partir de eventos que el llamador ya aporta, sin tocar `EventRepository`) de un elemento ya incluido, que se conserva mientras queden mensajes no-fuente que recortar. No se conecta a `ContextBuilder` ni al ensamblado de contexto (B6d), no reimplementa recuperación/relevancia (B6a/B6b) ni toca el presupuesto monetario (`adapters/llm/budget.py`, DR-018). Sin dependencias nuevas; sin clave real ni red; sin merge |

| 2026-07-21 | B6d | rama `feature/b6d-context-builder-integration-20260721-01`, PR pendiente | automática | `test_context_builder.py` (reescrito: schema real vía Alembic (`upgrade_to_head`) en vez de `Base.metadata.create_all`, porque `ContextBuilder` ya depende de `knowledge_fts`; orden de campos de `Context` con `decisions`; las consultas de cada caso ahora comparten término con el contenido del recuerdo/decisión que deben recuperar, para probar pertinencia real en vez de "toda memoria vigente"; nuevos casos: sección de decisiones ensamblada junto con memorias en `test_build_assembles_every_section`, exclusión de recuerdos/decisiones no relacionados con la consulta, tope de `max_knowledge_items` aplicado con SQLite real, protección de identidad/proyecto/mensaje actual con presupuesto de 1 token, mensajes recientes llenando el presupuesto restante con el más antiguo descartado primero); `test_render_instructions.py` (nuevos casos: sección "# Decisiones vigentes relacionadas" con contenido, su estado vacío seguro, y el orden de secciones completo identidad→proyecto→decisiones→recuerdos→mensajes; el caso previo "nunca menciona decisiones" se acotó al texto de la sección de proyecto, ya que la nueva sección sí las menciona por diseño); `test_send_message.py`, `test_memory_archive_delete_lifecycle.py`, `test_initial_project_persistence.py`, `test_secret_leakage.py`, `test_backup_restore_project_lifecycle.py`, `test_conversation_ui.py`, `test_main_window.py`, `test_composition_root_manual_memory.py` (todos adaptados a la firma ampliada de `ContextBuilder` y, donde construían el esquema a mano, a migración Alembic real) | Superada | Ruff format, Ruff lint y mypy estricto correctos; 1087 pytest (1080 previas + 7 nuevas) | Cierre de B6: contexto pertinente y limitado (SIRIUS-ARQ-0.1 S6.1; D-11; ATD-007). `Context` gana la sección `decisions: tuple[Decision, ...]` (solo APROBADAS/vigentes), colocada en el orden aprobado identidad→proyecto→decisiones vigentes relacionadas→recuerdos pertinentes→mensajes recientes→mensaje actual; `render_instructions()` añade "# Decisiones vigentes relacionadas" en ese lugar, de forma aditiva sobre `LLMRequest` (sin cambiar su contrato) y con estado seguro (cabecera sin viñetas) cuando no hay ninguna. `ContextBuilder.build()` ya no recupera "todas las memorias vigentes" ni un número fijo de mensajes: usa `current_user_message` como consulta de `RankRelevantKnowledgeUseCase` (B6b, reutilizado sin reimplementar), conserva el filtro de precedencia B4e existente (`find_prevailing_decision`) aplicado solo sobre recuerdos —nunca sobre decisiones— del resultado ya ordenado, calcula el coste en tokens de las secciones protegidas fijas (identidad con reglas/permisos, proyecto activo si existe, mensaje actual) con el `TokenCounter` (B6c) y se lo pasa como `protected_tokens` a `apply_context_budget` (B6c, reutilizado sin reimplementar) junto con el conocimiento ya ordenado y los mensajes recientes completos (acotados primero por `recent_messages_limit`, sin cambios, antes del recorte por presupuesto); resuelve los eventos-fuente de los candidatos vía `EventRepository.get_source` (una consulta por id, sin lista nueva del puerto) para la regla de supervivencia de mensaje-fuente de B6c. El resultado del presupuesto determina memorias, decisiones y mensajes recientes; identidad/reglas, proyecto activo y mensaje actual nunca se recortan, incluso con presupuesto ínfimo — nunca lanza excepción por eso. `composition_root` cablea `RankRelevantKnowledgeUseCase` y `CharacterHeuristicTokenCounter` (con `SqliteKnowledgeSearchRepository` añadido a `close_database_connections`) dentro de `ContextBuilder`, sin exponer SQLite/relevancia a `MainWindow`. `ContextBuilder` sigue siendo de solo lectura: no crea ni modifica datos ni índices. Cierra D-11 y B6 en su totalidad (B6a-B6d). Sin clave real ni red; sin merge |
| 2026-07-22 | B7a | rama `feature/b7a-actionable-error-messages-20260722-01`, PR pendiente | automática | `test_error_messages.py` (nuevo: cada `LLMErrorKind` distinto de `UNKNOWN` produce un mensaje distinto del genérico, parametrizado dinámicamente sobre `list(LLMErrorKind)` para que un valor nuevo del enum obligue a cubrirlo en `describe_error` en vez de caer en silencio al genérico; `UNKNOWN` y `None` producen el mismo mensaje genérico seguro; `failed_send_message` añade la referencia de soporte a cada mensaje; un mensaje con aspecto de clave/token del proveedor nunca aparece en el texto compuesto); `test_conversation_ui.py` (nuevo caso parametrizado sobre los nueve `LLMErrorKind` contra un proveedor simulado real: `error_label` muestra exactamente `describe_error(kind)` + la referencia del `operation_id` persistido, nunca el `LLMError.message` crudo del proveedor; caso de fallo de persistencia reforzado para comprobar que un fallo inesperado sin `error_kind` clasificado usa el mismo mensaje genérico y nunca la excepción cruda; caso de cancelación reforzado de `!= ""` a la comprobación exacta de "Envío cancelado." para dejar constancia de que esa rama no cambia) | Superada | Ruff format, Ruff lint y mypy estricto correctos; 1117 pytest (1087 previas + 30 nuevas) | Errores accionables en la conversación (RF-028; RNF-018; D-08, parte automatizable). Módulo nuevo, puro y sin Qt `sirius.presentation.error_messages` (`describe_error`, `failed_send_message`) mapea cada valor de `LLMErrorKind` (más el caso `None`) a un mensaje corto en español con una acción concreta, sin usar nunca `LLMError.message` del proveedor — solo `kind` y la referencia de soporte llegan a la interfaz. `MainWindow._on_finished` (rama `FAILED`) y `_on_crashed` (excepción inesperada del worker, sin `error_kind` disponible, reutiliza el helper con `None`) usan el mapeo en vez del texto genérico único anterior; la rama `CANCELLED` no se tocó. No se reimplementó `LLMErrorKind`, `LLMProvider` ni `send_message.py`; no se añadió el reintento sin reescribir (D-05, B7b) ni el aviso proactivo de presupuesto (D-09, B7c). Sin clave real ni red; sin merge |
| 2026-07-22 | B7b | rama `feature/b7b-retry-failed-send-20260722-01`, PR pendiente | automática | `test_conversation_ui.py` (nuevos casos: "Reintentar" oculto por defecto; un envío `FAILED` lo muestra y, al pulsarlo, reenvía exactamente el mismo texto bajo un `operation_id` nuevo, sin repoblar `message_input`, y lo oculta de nuevo tras un reintento `COMPLETED` — cubierto tanto para el fallo clasificado (`LLMError`) como para el crash inesperado del worker (`_on_crashed`), con un `_CrashingLLMProvider` nuevo para este último; un envío `CANCELLED` nunca lo muestra; empezar un envío nuevo limpia el estado de reintento pendiente incluso antes de que termine; oculto mientras hay un envío en curso); `test_main_window.py` (nuevo caso: "Reintentar" queda deshabilitado durante una operación de copia de seguridad y se reactiva al terminar, reutilizando `_BlockingCreateBackupUseCase` ya existente) | Superada | Ruff format, Ruff lint y mypy estricto correctos; 1132 pytest (1117 previas + 15 nuevas) | Reintento de un envío fallido sin reescribirlo (RF-007; D-05, cierre de su parte automatizable). `MainWindow` (presentación) añade únicamente el mínimo estado y control de UI descritos en el alcance: `_last_failed_text` (texto del último intento `FAILED`/crasheado, fijado en `_on_finished`/`_on_crashed`) y `_active_send_text` (texto en vuelo, necesario porque `_on_crashed` no recibe un `SendMessageResult` del que leerlo); un botón "Reintentar" nuevo junto a "Enviar"/"Cancelar", visible solo cuando hay un fallo pendiente y deshabilitado durante un envío o una operación de copia/restauración (misma exclusión mutua que un envío normal). `_handle_send_clicked`/`_handle_retry_clicked` comparten un único `_start_send(text)` que limpia el estado de reintento pendiente y genera un `operation_id` nuevo; "Reintentar" nunca toca `message_input`. No se cambiaron `SendMessageUseCase`, `send_message.py`, `SendMessageWorker`, `LLMProvider` ni ningún adaptador; el reintento nunca es automático. Sin clave real ni red; sin merge |
| 2026-07-22 | B7c | rama `feature/b7c-budget-warning-20260722-01`, PR pendiente | automática | `test_budget_status.py` (nuevo: por debajo del umbral no está cerca del límite; en el umbral y por encima de él sí; gasto cero nunca está cerca del límite; lee el año-mes UTC actual del repositorio; los umbrales configurados se propagan sin alterarse); `test_composition_root_budget_status.py` (nuevo: `get_budget_status_use_case` queda cableado; por defecto refleja el sobre de DR-018 —20/15 USD— sin gasto registrado; lee el mismo `LLMUsageRepository` año-mes que el `BudgetTracker` del proveedor OpenAI usaría, escribiendo gasto real vía una instancia distinta de repositorio contra el mismo fichero); `test_main_window.py` (nuevos casos: aviso oculto con gasto por debajo del umbral; aviso con las cantidades exactas al alcanzar el umbral; el proveedor simulado nunca lo muestra tras enviar mensajes reales, porque nunca registra gasto; el aviso permanece oculto mientras un envío sigue en curso —aunque el gasto ya haya cruzado el umbral— y solo se recalcula tras `_on_finished`) | Superada | Ruff format, Ruff lint y mypy estricto correctos; 1145 pytest (1132 previas + 13 nuevas) | Aviso proactivo de presupuesto mensual (RF-030; PA-018; DR-018), cierre de D-09 en su parte automatizable y de B7 entero. Caso de uso nuevo y puro `sirius.application.budget_status.GetBudgetStatusUseCase` (`BudgetStatus`: `spent_usd`, `warn_threshold_usd`, `monthly_limit_usd`, `is_near_limit`), deliberadamente sin depender de `sirius.adapters.llm.budget.BudgetTracker`/`BudgetPolicy` (la capa de aplicación nunca importa `sirius.adapters`, `test_application_boundaries.py`): depende solo del `Protocol` mínimo `LLMSpendReader` (`get_spent_usd`), que `SqliteLLMUsageRepository` ya satisface estructuralmente sin cambios. `composition_root` construye el caso de uso con la **misma instancia** de `llm_usage_repository` que `_build_llm_provider` entrega al `BudgetTracker` real del proveedor OpenAI, y con `warn_threshold_usd=BudgetPolicy().warn_threshold_usd` (15 USD, DR-018, sin exponer ni permitir cambiarlo) y `monthly_limit_usd` tomado de la misma resolución de `provider_settings.monthly_budget_usd` que ya usa `_build_llm_provider` — ambas lecturas siempre concuerdan sobre el gasto del mes. `MainWindow` añade una etiqueta nueva de solo texto (`budget_warning_label`, nunca un diálogo modal: el envío nunca se bloquea por esto) en la pestaña "Conversación", recalculada en `_load_history` (al abrir la conversación) y al final de `_on_finished` (tras cada envío completado, cualquiera que sea su desenlace) — nunca durante un envío en curso. No se tocaron los umbrales/montos de DR-018, el bloqueo ya existente en `OpenAIResponsesProvider`/`BudgetTracker`, ni `LLMProvider`/`send_message.py`/`SendMessageWorker`. Sin clave real ni red; sin merge |

| 2026-07-22 | B8a | rama `feature/b8a-safe-markdown-rendering-20260722-01`, PR pendiente | automática | `tests/gui/test_conversation_ui.py` (nuevos casos: Markdown con encabezado/negrita/cursiva/lista/código en línea/bloque de código se muestra renderizado, nunca con la sintaxis literal; un mensaje con `<script>...</script>`/`<b onclick=...>` se muestra literal y escapado, nunca interpretado; streaming muestra el delta como texto plano sin renderizar y el resultado final consolida a Markdown seguro, con un proveedor de bloqueo determinista (`_BlockingMarkdownProvider`) en vez de una espera arbitraria; los sufijos `(cancelado)`/`(fallido)` y el marcador `(mensaje redactado)` se preservan en el widget renderizado) | Superada | Ruff format, Ruff lint y mypy estricto correctos; 1151 pytest (1145 previas + 6 nuevas) | Primera mitad de Markdown seguro (RF-008; SP-07; D-06 parcial — la segunda mitad, bloques de código copiables, es B8b y queda fuera). `MessageItemWidget`/`_MessageBody` (nuevo, `sirius.presentation.message_view`) renderizan cada mensaje con el Markdown nativo de Qt (`QTextDocument.setMarkdown` con `MarkdownDialectGitHub \| MarkdownNoHTML`, nunca `setHtml` con contenido del mensaje) insertados como `QListWidget.setItemWidget`, sin tocar `QListWidgetItem.text()` (que sigue siendo la fuente de accesibilidad/compatibilidad ya cubierta por toda la suite existente, que pasó sin modificar ni una aserción). `MarkdownNoHTML` es la pieza de seguridad: sin ella, Qt interpreta o descarta en silencio HTML/script embebido en vez de mostrarlo literal, verificado experimentalmente antes de fijar la implementación. `QTextEdit` de solo lectura (no `QTextBrowser`): sus `textInteractionFlags` por defecto no incluyen navegación de enlaces, así que no hace falta `setOpenExternalLinks(False)`/`setOpenLinks(False)`; no hay carga de recursos externos ni red. El streaming (`_on_delta`) sigue mostrando el delta acumulado, ahora como texto plano sin interpretar (más simple y estable, decisión explícitamente permitida por la incidencia); `_on_finished` consolida el texto final como Markdown seguro. Los estados `CANCELLED`/`FAILED`/`REDACTED` no cambiaron de lógica (`_compose_markdown_body`, extraído sin alterar el comportamiento ya probado de `_set_item_text`). Sin dependencias nuevas (Qt nativo); sin clave real ni red; sin merge |
| 2026-07-22 | B8b | rama `feature/b8b-copyable-code-blocks-20260722-01`, PR pendiente | automática | `tests/gui/test_conversation_ui.py` (nuevos casos: un bloque de código cercado muestra exactamente un botón "Copiar" que, al pulsarlo, deja en el portapapeles (`QApplication.clipboard()`) el código exacto sin vallas ni identificador de lenguaje; varios bloques en el mismo mensaje muestran un botón cada uno y cada uno copia solo el suyo; un mensaje sin ningún bloque cercado no muestra ningún botón y sigue viéndose como en B8a; la prosa antes/entre/después de los bloques conserva su orden original; `<script>...</script>`/`<b onclick=...>` dentro de un bloque de código se muestran y copian literales, nunca interpretados (SP-07 dentro del bloque); streaming con un proveedor de bloqueo determinista nuevo (`_BlockingCodeBlockProvider`) confirma que el delta en vuelo no muestra ningún botón —sigue sin segmentar, B8a— y que el resultado final consolidado sí segmenta el bloque y muestra su botón) | Superada | Ruff format, Ruff lint y mypy estricto correctos; 1157 pytest (1151 previas + 6 nuevas) | Segunda mitad de Markdown seguro: bloques de código copiables (RF-008; SP-07), cierre de D-06 junto con B8a. `MessageItemWidget` (`sirius.presentation.message_view`) segmenta de forma determinista el texto consolidado por sus vallas de bloque de código (```` ``` ````, vía una única expresión regular con `re.DOTALL` que exige un salto de línea tras la valla de apertura y localiza la siguiente valla literal de cierre) en una secuencia ordenada de tramos: cada tramo de prosa se sigue renderizando con `_MessageBody`/`setMarkdown` de B8a sin ninguna reimplementación, y cada bloque de código nuevo (`_CodeBlockWidget`) reutiliza la misma `_MessageBody` en modo texto plano (`set_plain_content`, nunca Markdown ni HTML) con una fuente monoespaciada y un botón "Copiar" que llama a `QApplication.clipboard().setText(...)` con el código exacto — sin las vallas, sin el identificador de lenguaje tras la valla de apertura, y sin el salto de línea final que solo es el terminador de la última línea de código. Un mensaje sin vallas cercadas produce exactamente un tramo de prosa, así que se renderiza idéntico a B8a (ningún botón). El streaming (`_on_delta`/`set_streaming_text`) no cambió: sigue mostrando el delta acumulado como un único tramo de texto plano sin segmentar; solo `_on_finished`/`set_message` segmenta el texto final. `rendered_plain_text()`/`rendered_html()` ahora concatenan todos los tramos (prosa y código) en orden, por lo que las aserciones de B8a sobre bloques de código cercados siguieron pasando sin modificarlas. Sin resaltado de sintaxis por lenguaje (no es requisito de RF-008); sin dependencias nuevas (solo Qt); sin clave real ni red; sin merge |
| 2026-07-22 | B9a | rama `feature/b9a-export-structured-service`, PR pendiente | automática | `test_filesystem_export_service.py` (nuevo: nombre del directorio derivado del `Clock` inyectado; exactamente los seis elementos de S12.1; `manifest.json` con formato/versión de aplicación/versión de esquema determinista/fecha/lista de archivos; `conversation.jsonl` con un mensaje por línea en orden, rol, contenido, estado, fecha, `operation_id`, `identity_version`; `project.json` con `null` documentado sin proyecto configurado —incluido el placeholder de arranque sin revisión— y con el proyecto activo y su revisión vigente cuando existe; `memories.jsonl`/`decisions.jsonl` con un elemento vigente por línea; `README.txt` con la advertencia de datos personales y la ausencia de la clave API; rechazo explícito a sobrescribir una exportación ya existente; ningún directorio parcial ante un fallo de escritura, vía directorio de staging + `os.replace` atómico); `test_export_structured_use_case.py` (nuevo: el caso de uso reúne conversación/proyecto activo/recuerdos vigentes/decisiones vigentes desde los puertos existentes y delega la escritura en el servicio, sin crear conversación ni listar mensajes cuando no existe ninguna); `test_composition_root_export.py` (nuevo: `export_structured_use_case` queda cableado); `tests/integration/test_export_structured.py` (nuevo, contra SQLite real migrado con Alembic y los casos de uso reales de B3/B4: nombre de directorio determinista, los seis archivos exactos, ausencia de proyecto sin fallar, datos reales de conversación/proyecto/recuerdo/decisión —incluida una segunda decisión aún PROPOSED que nunca aparece en `decisions.jsonl`—, y prueba explícita de que la exportación nunca modifica un solo byte de la base de datos origen); `tests/integration/test_secret_leakage.py` (nuevo caso `test_key_never_appears_in_a_structured_export`: con una clave falsa configurada en el almacén de secretos y datos reales de conversación/proyecto/memoria/decisión, ninguno de los seis archivos exportados contiene la clave) | Superada | Ruff format, Ruff lint y mypy estricto correctos; 1177 pytest (1157 previas + 20 nuevas) | Servicio y caso de uso de exportación estructurada, abierta y legible, sin interfaz todavía (B9a de B9/D-07; RF-031; PA-020; ATD-009 "exportación abierta"; SIRIUS-ARQ-0.1 S12.1). Puerto nuevo `sirius.ports.clock.Clock` (`utc_now()`, S4) con su adaptador de producción `SystemClock` y su doble determinista `FakeClock` (ambos en `sirius.adapters.clock`), inyectado en el adaptador de exportación exactamente como exige la arquitectura para que el nombre del directorio sea reproducible en pruebas. Puerto nuevo `sirius.ports.export.ExportService` (`export_structured(destination_dir, *, messages, project, memories, decisions) -> Path`) y su adaptador `FilesystemExportService` (`sirius.adapters.export`): calcula `sirius-export-YYYYMMDD-HHMM` a partir del `Clock` inyectado (nunca `datetime.now()` directamente), escribe los seis elementos exactos del formato aprobado en UTF-8 dentro de un directorio de staging oculto y solo lo publica con un `os.replace` atómico al final — un fallo a mitad de escritura nunca deja un directorio parcial visible, y una segunda llamada con el mismo minuto nunca sobrescribe una exportación ya creada. `ExportStructuredUseCase` (`sirius.application.export_structured`) reutiliza sin cambios los puertos de solo lectura ya existentes (`ConversationRepository.get_main_conversation()`/`list_messages()`, `ProjectRepository.get_active_project()`, `MemoryRepository.list_current_memories()`, `DecisionRepository.list_current_decisions()`) — nunca crea la conversación si no existe todavía, nunca escribe nada — y delega la escritura real en el servicio. `project.json` documenta la ausencia con `null` tanto cuando no hay proyecto como cuando solo existe el placeholder de arranque sin configurar (`sirius.domain.project.is_configured()`), sin lanzar ninguna excepción. RNF-013 verificado explícitamente: `ExportService`/`ExportStructuredUseCase` no reciben nunca un `SecretStore` ni tocan la clave API, comprobado además con una clave falsa real configurada en el almacén de secretos. `composition_root.build_conversation_dependencies` cablea `export_structured_use_case` (nuevo campo de `ConversationDependencies`) sin exponer ninguna acción de interfaz: ningún código de presentación lo llama todavía, porque el aviso previo de datos personales, el hilo en segundo plano (`QThreadPool`) y mostrar la ruta resultante son B9b, un corte posterior y distinto. No cambia el modelo de datos, migraciones, el proveedor ni `send_message.py`; no toca el formato cifrado de copia de seguridad (`BackupService`, ya implementado y distinto de esta exportación abierta). Sin clave real ni red; sin merge |
| 2026-07-22 | B9b | rama `feature/b9b-export-action`, PR pendiente | automática | `tests/gui/test_export_ui.py` (nuevo: el botón "Exportar" muestra primero el aviso de datos personales/sin clave API antes de llamar al caso de uso; cancelar el aviso nunca lo llama; confirmar el aviso pero cancelar la selección de carpeta tampoco lo llama; confirmar ambos llama exactamente una vez con la carpeta elegida, en segundo plano —`_BlockingExportStructuredUseCase` determinista, sin espera arbitraria—; éxito muestra la ruta exacta creada; `ExportError` muestra su mensaje seguro verbatim; un crash inesperado del worker muestra el mensaje genérico y nunca la traza; exportar deshabilita "Enviar", "Crear copia cifrada", "Validar copia" y "Restaurar copia" mientras está en curso y los reactiva al terminar; exportar se bloquea si ya hay un envío o una operación de copia/restauración en curso, y viceversa —enviar o iniciar una copia mientras exportar está en curso no llama a su caso de uso—); se añadió `export_structured_use_case=dependencies.export_structured_use_case` a los constructores de `MainWindow`/`ValidatedMainWindow` en `tests/gui/test_main_window.py`, `test_conversation_ui.py`, `test_settings_ui.py`, `test_validated_main_window.py` y `test_backup_recovery_ui.py`, sin debilitar ninguna aserción existente | Superada | Ruff format, Ruff lint y mypy estricto correctos; 1189 pytest (1177 previas + 12 nuevas) | Acción "Exportar" en la interfaz, con aviso previo obligatorio y ejecución en segundo plano (B9b de B9, cierre de D-07; RF-031; PA-020; SIRIUS-ARQ-0.1 S12.1 y S10.2). Nuevo grupo "Exportación de datos" en la pestaña "Configuración" (`MainWindow._build_export_group`), junto a "Copia de seguridad y restauración", con un único botón "Exportar": al pulsarlo, un `QMessageBox` de confirmación (`_confirm_export`, seam inyectable como `confirm_restore`) explica que la exportación puede contener información personal y que nunca incluye la clave de API; cancelarlo nunca llama a `ExportStructuredUseCase` (verificado explícitamente). Solo tras confirmar se pide la carpeta destino (`_choose_export_directory`, seam inyectable como `choose_backup_file`, por defecto `QFileDialog.getExistingDirectory`); cancelar la selección tampoco exporta. `ExportWorker` (nuevo, `sirius.presentation.export_worker`, mismo patrón que `backup_worker.py`) ejecuta `ExportStructuredUseCase.export_structured` en el `QThreadPool` ya existente, nunca en el hilo GUI; `ExportError` se muestra verbatim (mensaje ya documentado como seguro) y cualquier otra excepción se registra solo por su tipo y se traduce en el mismo mensaje genérico que ya usan copia/restauración. Éxito muestra la ruta exacta devuelta por el caso de uso. Exclusión mutua nueva y simétrica vía `_is_export_busy`: exportar comprueba `_is_sending`/`_is_backup_busy` antes de arrancar (igual que copia/restauración ya hacían entre sí) y, a la inversa, enviar y las tres operaciones de copia ahora también comprueban `_is_export_busy`; mientras exporta está en curso se deshabilitan "Enviar", el campo de mensaje y los controles de copia/restauración (reutilizando `_set_backup_controls_enabled`), y se reactivan al terminar exactamente como hace `_finish_backup_operation`. `ValidatedMainWindow` y `sirius.main._build_main_window` propagan `export_structured_use_case` sin ningún otro cambio. No se tocó `ExportStructuredUseCase`, `ExportService`/`FilesystemExportService` ni el formato de B9a; no se tocó la copia cifrada. `test_presentation_boundaries.py` sigue verde: la presentación solo importa `ExportStructuredUseCase` (aplicación) y `ExportWorker` propio, nunca un adaptador. Sin clave real ni red; pruebas de GUI con `QT_QPA_PLATFORM=offscreen`; sin merge |
| 2026-07-22 | B10 | rama `feature/b10-external-actions-policy`, PR pendiente | automática | `test_identity_domain.py` (nuevo caso: la semilla canónica de personalidad incluye, en su texto exacto, el rechazo de acciones externas de RF-035); `test_render_instructions.py` (nuevo caso: instanciando la identidad con la semilla canónica real `INITIAL_PERSONALITY_INSTRUCTIONS`, `render_instructions()` sobre ese contexto contiene esa misma política, verificando que llega íntegra a las instrucciones renderizadas para el proveedor) | Superada | Ruff format, Ruff lint y mypy estricto correctos; 1191 pytest (1189 previas + 2 nuevas) | Política RF-035 "Sin acciones externas" (A-01, parte automatizable de PA-024). `INITIAL_PERSONALITY_INSTRUCTIONS` (`sirius.domain.identity`) gana un párrafo final con redacción tomada literalmente del canónico de Producto (S3/S5 "Límite de ayuda" + S10 RF-035, sin texto inventado): "Sirius ayuda mediante conversación, razonamiento, planificación, revisión y registro; no ejecuta acciones externas y rechaza las solicitudes de ejecutar archivos, comandos, web o automatizaciones, por estar fuera del alcance de 0.1." La política queda dentro de las reglas de la identidad (SIRIUS-ARQ-0.1 S6.1) y se renderiza sin cambios de contrato porque `render_instructions()` ya emitía `personality_instructions` verbatim. No se añadió ninguna guardia de ejecución: Sirius 0.1 no tiene ruta de código capaz de ejecutar archivos, comandos, web ni automatizaciones, así que RNF-024 se mantiene cumplido estructuralmente, sin nueva superficie. No se tocó `send_message.py` más allá de lo derivado del texto de identidad, ni el modelo de datos, ni `docs/canonical/**`. La prueba formal de que el modelo declina en runtime (PA-024 con proveedor real) queda expresamente fuera de alcance, para V8.3. Sin clave real ni red; sin merge |
| 2026-07-22 | B11 | rama `feature/b11-forced-shutdown-recovery-test`, PR pendiente | automática | `test_forced_shutdown_recovery.py` (nuevo, contra SQLite real migrado con Alembic: escribe estado confirmado —conversación con mensajes COMPLETED de ambos roles, proyecto activo con su revisión vigente, un recuerdo manual— y un turno interrumpido a mitad de streaming (mensaje USER `COMPLETED` sin fila SIRIUS, porque `send_message.py` solo la escribe al terminar el streaming), abandona esos repositorios y sus motores sin `close()` ordenado en vez de cerrarlos, y reabre con repositorios nuevos + `initialize_persistence()`: la conversación principal, la identidad y el proyecto activo no se duplican; los mensajes confirmados y el recuerdo sobreviven con su contenido exacto; el turno interrumpido deja únicamente su fila USER, sin fila SIRIUS parcial ni corrupta; `PRAGMA integrity_check` devuelve `ok`; una segunda reapertura tras la primera sigue sin duplicar nada) | Superada | Ruff format, Ruff lint y mypy estricto correctos; 1192 pytest (1191 previas + 1 nueva) | Cierre de B11, último bloque de código de V8.1 (A-02; RNF-005/006; parte automatizable de PA-019). La recuperación tras cierre forzado ya estaba cubierta por diseño desde antes de este bloque —cada escritura de repositorio se confirma en su propia transacción SQLite vía `session_scope`, los mensajes de Sirius se persisten enteros solo al terminar el streaming (nunca una fila parcial), e `initialize_persistence()` ya recargaba el estado de forma idempotente al arrancar—, pero no existía ninguna prueba que lo demostrara ni una afirmación explícita de la durabilidad; B11 añade ambas sin cambiar ese diseño. La única línea de producción tocada es `build_engine` (`adapters/persistence/database.py`): el listener `connect` ya existente que fija `PRAGMA foreign_keys=ON` ahora también fija `PRAGMA synchronous=FULL` junto a él, para afirmar la durabilidad explícitamente en vez de depender de un valor por defecto implícito de SQLite — cambio conservador que no altera ningún comportamiento observable (ninguna prueba existente cambió) y no toca el modo de journal (sigue el rollback journal por defecto; WAL queda fuera de alcance, ver la incidencia). La prueba nueva simula el cierre forzado abandonando deliberadamente cada repositorio/motor sin llamar a `close()`/`dispose()` en vez de cerrarlos de forma ordenada, tal como haría un proceso realmente matado, y reabre con instancias completamente nuevas contra el mismo fichero. No se tocó `send_message.py`, el modelo de datos, migraciones destructivas, el proveedor, Producto, Arquitectura ni ATD. La prueba manual PA-019 (matar el proceso de verdad en Windows) queda fuera de alcance, para V8.2. Sin clave real ni red; sin merge |

| 2026-08-10 | B1 | `b0beab4` (PR #144) | documental | `test_documentation_single_source.py` | Superada | CI verde, 1527 pruebas | ADR-005: el estado de V8 pasa a vivir solo en la tabla de bloques de este archivo. Cuatro mutaciones verificadas |
| 2026-08-10 | B12a | `03bede4` (PR #145) | automática | `test_pa_sp_traceability.py` | Superada | CI verde, 1649 pruebas | ADR-006: los 40 identificadores del plan quedan enlazados y comprobados por máquina. Siete mutaciones verificadas, incluida el renombrado de una prueba real |
| 2026-08-10 | B12c | rama `claude/ciclo-pendientes-prs-issues-qm4t8x` | automática | `test_local_performance.py` | Superada con hallazgo | 1653 pruebas en verde; cifras en la sección de rendimiento de arriba | ADR-007. **No declara PA-025 superada.** Destapa que construir el contexto usa entre el 89 % y el 100 % de sus 300 ms; causa localizada en `list_current_memories()`. Cinco mutaciones verificadas |
| 2026-08-11 | B12e | rama `fix/b12e-sqlite-list-n-plus-1` (incidencia #148) | automática | `test_memory_decision_list_query_count.py`; `test_memory_decision_list_sqlite_variable_limit.py`; `test_local_performance.py` | Superada | CI verde, 1659 pruebas (1653 previas + 6 nuevas); cifras antes/después en la sección de rendimiento de abajo | ADR-008. Corrige el N+1 que ADR-007 localizó, sin cambiar lo que devuelven los cuatro métodos. Cuatro mutaciones verificadas: con el N+1 restaurado, las cuatro pruebas de conteo fallan; restaurado el arreglo, pasan. Ronda 2 (revisión CODEX-001 de la PR #149): el `IN (...)` sin trocear podía fallar con `OperationalError: too many SQL variables` por encima de `SQLITE_LIMIT_VARIABLE_NUMBER`; `_load_memories()`/`_load_decisions()` ahora trocean en lotes de ese límite. Dos mutaciones verificadas: con el troceo revertido, las dos pruebas nuevas fallan con ese mismo error; con el arreglo, pasan |
| 2026-08-10 | B13 | commit `3432253`, rama `feat/b13-reproducible-windows-package`; artefacto `Sirius-0.1.0.dev0-3432253-windows-x64` | manual-Windows | `scripts/build_windows.ps1` y `scripts/verify_windows_package.ps1` dos veces cada uno desde un checkout limpio fuera de OneDrive (`C:\dev\sirius`). **77 comprobaciones, 0 fallos, 3 omitidas** en ambas verificaciones; **inventario relativo identico** entre las dos construcciones (109 rutas comparadas una a una) | Superada con reservas | Compilacion 1125.2 s y 1036.6 s; ZIP `988613c0...` y `2a1e8d9e...`; Windows 11 Pro 10.0.26200.0, MSVC `cl` 19.44.35228, Windows SDK 10.0.26100.0, Python 3.14.6, PySide6/Qt 6.11.1, Nuitka 4.1.3, uv 0.11.28, head de Alembic `61be4bb269bf`, 24 tablas | Las 3 omisiones son la misma: el arranque sin clave no es observable en una sesion de Windows con la credencial guardada; es de B14. Hash del ZIP distinto entre las dos, como se declara. Cuatro defectos del proceso corregidos en esta pasada: `7a96c1a` modo de enlace de uv contra el filtro de nube de OneDrive; `839d6ff` la puerta de credencial hacia imposible verificar en la unica maquina donde se construye; `e9d51c7` `pyside6-deploy` colgaba el build 50 minutos esperando una respuesta invisible; `3432253` la clcache interna de Nuitka fallaba en las 15 unidades que intento. Ver `docs/implementation/B13_PACKAGING.md` |
| 2026-08-10 | B14 | commit `567ca94`, rama `feat/b13-reproducible-windows-package` | manual-Windows | `scripts/verify_windows_no_network.ps1` sobre el `Sirius.exe` del artefacto, sin elevar y en entorno desechable. Vigilancia del arbol de procesos completo cada 250 ms: **45 muestras, ninguna conexion saliente** | Superada con reservas | 11 comprobaciones, 0 fallos, 1 omitida; 10 pruebas estructurales en `tests/unit/test_verify_windows_no_network_safety.py` | Cierra la partida 2 de las 9 de B14. Omision: destinos UDP, DNS incluido, que no se pueden observar sin captura de paquetes y eso exigiria administrador. La partida 3 (valor senuelo en Credential Manager) queda aplazada por decision del usuario. Marcador en `docs/implementation/B14_WINDOWS_SIN_CLAVE.md` |
| 2026-08-10 | B14 | paquete `Sirius-0.1.0.dev0-3432253-windows-x64` instalado en `%LOCALAPPDATA%\Programs\Sirius` | manual-Windows | Dos pruebas manuales **ejecutadas y reportadas por el propietario**: la partida 3 de B14 (valor senuelo en Windows Credential Manager) y **PA-019** (cierre forzado: terminar el proceso durante una operacion y comprobar que se recupera el ultimo estado consistente sin corrupcion) | Superada segun el propietario | Declaracion del propietario en la sesion del 2026-08-10. Sin captura automatica: una prueba manual la pasa quien la ejecuta, y este registro dice quien la reporto | **Cierra B14.** La partida 3 es ademas una de las puertas de V8.3 («Credential Manager haya sido comprobado con un valor senuelo»). PA-019 cubre la mitad manual de **A-02**. No convierte a B15 en desbloqueado: V8.3 sigue exigiendo D-01, D-02 y D-10 cerrados y la **autorizacion expresa del propietario** para obtener y usar una clave temporal |
| 2026-08-10 | B15 y B16 | paquete `Sirius-0.1.0.dev0-3432253-windows-x64`, con clave y proveedor reales | proveedor-real + evaluacion-humana | Pruebas de aceptacion **ejecutadas y declaradas superadas por el propietario**: **PA-002** (una clave invalida se rechaza, se explica y no se guarda), **PA-001** (una clave valida valida, se protege y abre la conversacion), **PA-008** (decisiones y bloqueos registrados, cerrar, volver dias despues: siguen ahi y las decisiones siguen vigentes), **PA-009** (preguntar por el siguiente paso: la recomendacion cuadra con el estado real), **PA-023** (trafico real: solo hacia el proveedor configurado), **PS-01 a PS-07** (conversacion, decision tecnica, desacuerdo, incertidumbre, error grave, frustracion y tarea larga) y **PA-E2E-01** (proyecto real durante varias sesiones) | Superadas segun el propietario | Declaracion del propietario en la sesion del 2026-08-10. La suite automatica completa quedo en verde el mismo dia sobre el arbol fusionado con `main`: 2285 pruebas, 0 fallos, 2 omitidas (QtMultimedia ausente en el runner, MS-A02) | **Cierra B15 y B16, y con ellos los 16 bloques.** Alcance exacto de la declaracion, dicho sin adornos: son pruebas **manuales y de juicio humano**, y quien las pasa es quien las ejecuta; no hay captura automatica de ninguna. **PS-01 a PS-07 se reportaron como un juicio global sobre las siete**, no como siete veredictos separados, de modo que quien lea esto no confunda una impresion de conjunto con siete evaluaciones independientes. Las omisiones declaradas antes siguen en pie: destinos UDP en la partida 2 de B14, y los flujos de PA-020, PA-021 y PA-022 pulsados dentro del `.exe`. **Declarar Sirius 0.1 aceptada y terminada corresponde al propietario, no a esta tabla** |

Tipos permitidos: `automática`, `CI`, `manual-Windows`, `proveedor-real`, `evaluación-humana`, `documental`.

### Rendimiento local sobre el conjunto de referencia (2026-08-10, B12c)

30 repeticiones por operación sobre 5.000 mensajes, 500 recuerdos, 100
decisiones versionadas y 10 proyectos con uno activo. Tres pasadas del mismo
código en la misma máquina. Runner de CI (Linux), **no** el Windows del
usuario: esto no declara PA-025 superada.

| Operación | P95 pasada 1 | pasada 2 | pasada 3 | Límite |
|---|---|---|---|---|
| inicio (rutas, migraciones, repositorios) | 30,3 ms | — | — | 3.000 ms |
| listar decisiones vigentes | 25,4 ms | 22,8 ms | 25,8 ms | 300 ms |
| cargar historial completo | 99,1 ms | 123,1 ms | 120,1 ms | 300 ms |
| listar recuerdos vigentes | 117,4 ms | 122,5 ms | 115,3 ms | 300 ms |
| resumen de conocimiento | 154,5 ms | 132,0 ms | 136,3 ms | 300 ms |
| **construir contexto** | **266,4 ms** | **286,6 ms** | **298,6 ms** | **300 ms** |

**Riesgo abierto para PA-025.** Construir el contexto usa entre el 89 % y el
100 % de su presupuesto. Causa localizada en el código:
`SqliteMemoryRepository.list_current_memories()` ejecuta 501 consultas para 500
recuerdos porque `_load_memory()` pide la revisión vigente una por una.
Corregirlo es un cambio de código productivo, fuera del alcance de B12c, y
espera decisión del propietario. Ver ADR-007.

### Rendimiento local sobre el conjunto de referencia (2026-08-11, B12e)

Mismo conjunto de referencia, misma máquina, mismo runner de CI (Linux) que la
medición de B12c. Una pasada antes del arreglo (código de `main` en
`97676e1`) y una después, 30 repeticiones por operación:

| Operación | P95 antes (B12c, `main`) | P95 después (B12e) | Límite |
|---|---|---|---|
| listar recuerdos vigentes | 104,7 ms | 9,3 ms | 300 ms |
| listar decisiones vigentes | 20,3 ms | 2,2 ms | 300 ms |
| resumen de conocimiento | 125,4 ms | 12,6 ms | 300 ms |
| cargar historial completo | 87,9 ms | 94,2 ms | 300 ms |
| **construir contexto** | **239,8 ms** | **120,9 ms** | **300 ms** |

Construir el contexto pasa del 80 % al 40 % de su presupuesto de 300 ms.
`listar recuerdos vigentes` y `listar decisiones vigentes` —las dos
operaciones que tenían la forma N+1 (`list_archived_memories()` y
`list_archived_decisions()` la comparten, pero el conjunto de referencia no
tiene elementos archivados que medir aquí)— caen a menos del 10 % del límite.

**No cambia qué devuelven los cuatro métodos corregidos.**
`test_sqlite_memory_repository.py`, `test_sqlite_decision_repository.py`,
`test_memory_archive_delete_lifecycle.py`, `test_decision_lifecycle.py` y
`test_decision_archive_lifecycle.py` —que no se tocaron— siguen en verde y son
la prueba de ello.

**PA-025 sigue sin declararse superada.** Este runner es Linux compartido, no
el Windows del usuario; el criterio de ADR-007 sobre cuándo se afirma el
límite del plan en CI no cambia con B12e.

### Asientos correctores (2026-08-10)

Las filas de este registro son evidencia fechada y no se reescriben. Lo que
cambió después se apunta aquí debajo, que es como se corrige un libro de
registro.

- Las filas del 22 de julio de B8a, B8b, B9a, B9b, B10 y B11 dicen «PR
  pendiente». Las seis se fusionaron: B8a en la PR #101 (`35659a3`), B8b en la
  #103 (`135a032`), B9a en la #105 (`3221553`), B9b en la #107 (`cf9688a`),
  B10 en la #109 (`586438b`) y B11 en la #111 (`cbebcbd`).
- **A-03 (empaquetado reproducible) — cerrado sin evidencia registrada.** El
  propietario declaró el 10 de agosto de 2026 que las ejecuciones de build y
  verify en Windows ya están hechas, y autorizó darlo por bueno sin adjuntar
  su salida. No hay, por tanto, ninguna fila de tipo `manual-Windows` que lo
  sostenga: A-03 es una puerta de V8.3 y hoy está cerrada sobre una
  declaración, no sobre una comprobación. Queda escrito para que quien abra
  V8.3 sepa exactamente qué respalda esa puerta.

## Estado de pruebas de aceptación

Estados permitidos: `no preparada`, `preparada`, `automática superada`, `manual pendiente`, `superada`, `fallida`, `bloqueada`.

| Grupo | Estado | Dependencia principal |
|---|---|---|
| PA-001 a PA-025 | Superada por declaración del propietario el 2026-08-10 | Ejecutadas por el propietario con el proveedor real. Trazado formal en `TRAZABILIDAD_PA_SP.md` (B12a). PA-019 y la partida 3 de B14 constan aparte, en la fila de evidencia de B14 |
| PS-01 a PS-07 | Superada por declaración del propietario el 2026-08-10 | Evaluación humana del propietario, reportada como un juicio global sobre las siete y no como siete veredictos separados. Consta así en la fila de evidencia |
| SP-01 a SP-07 | Superada por declaración del propietario el 2026-08-10 en su parte manual | Su parte automatizable estaba cubierta; la manual la ejecuta el propietario. Windows real y proveedor real, ambos disponibles |
| PA-E2E-01 | Superada por declaración del propietario el 2026-08-10 | Proyecto real durante varias sesiones, con las decisiones y los bloqueos recuperados al volver |

Que un comportamiento esté cubierto por pruebas automáticas **no** convierte su
PA en superada. Qué está cubierto y con qué prueba se lee en
`docs/implementation/TRAZABILIDAD_PA_SP.md`, comprobado por máquina (ADR-006);
la declaración formal de una PA superada ocurre en V8.3 y V8.4. Aquí no se
escribe la cuenta a mano: caduca en el siguiente merge y vuelve a afirmar lo
que ya no es cierto.

## Anexo histórico: fichas de bloque hasta B3c

**Este anexo no es estado.** Es el detalle congelado de los bloques que se
ficharon uno a uno entre B2a y B3c, conservado por su valor de registro. Se
detiene en B3c porque a partir de B4 el detalle dejó de fichar aquí; el estado
vigente de todos los bloques está en la tabla de bloques operativos, que es la
única autoritativa (ADR-005). No añadir fichas nuevas a este anexo.

Las PR que fusionaron cada subbloque: B2a #24 (`f7134ca`), B2b #26 (`2c60afc`),
B3a #27 (`882ab62`), B3b #28 (`a2f74df`), B3c #29, B4a #36, B4b #37, B4c #39,
B4d, B4e #52, B4f, B5 #79 (`7370a19`), B6a #82, B6b #84, B6c #86, B6d #91,
B7a #93, B7b #97, B7c #99, B8a #101, B8b #103, B9a #105, B9b #107, B10 #109,
B11 #111.

Una nota que conviene no perder: la PR de B4d **no** activó la revisión
automática por incidencia `agent-review-requested`, a diferencia de las de B4b
y B4c. Aquella autorización puntual no se extendió a B4d (ver
`AUTOMATION_OPERATING_CONTRACT.md` §2/§10).

### B2a — Primera configuración básica — FUSIONADA (PR #24, squash `f7134ca658e6343779ee6bfe89ad05dd2f0a8ba3`)

Este corte dentro de B2 detecta el estado real de "primera apertura" (ausencia de
clave configurada, mediante `ApiKeySettingsUseCase.has_key()` ya existente) y,
solo en ese estado, presenta un paso distinto de la vista normal
(`OnboardingWindow`, ventana propia construida en `sirius.main`) que:

- detecta ausencia de credencial mediante `ApiKeySettingsUseCase.has_key()`;
- muestra qué datos permanecen locales y qué se envía al proveedor;
- muestra proveedor y modelo predeterminados;
- solicita únicamente la clave;
- reutiliza RF-002 (`ValidateAndSaveApiKeyUseCase`, `CredentialValidationWorker`)
  para validar y guardar;
- tras éxito, activa el proveedor real en la misma ejecución (nueva
  `ConversationDependencies.activate_configured_llm_provider`: selecciona "openai"
  en la configuración no sensible existente y reconstruye el proveedor sobre
  `SendMessageUseCase.set_llm_provider`, sin reiniciar SQLite ni pedir un reinicio
  de Sirius) y abre la conversación principal usando la ruta local predeterminada
  existente (sin editarla en este corte).

Un bloque de texto permanente en Ajustes no equivale a esto: no distingue primera
apertura de uso normal ni conduce a ningún flujo.

La edición de la ruta local queda explícitamente fuera de B2a y pasa a **B2b**,
independiente: la ruta debe resolverse antes de inicializar SQLite y construir las
dependencias completas, no es una modificación limitada a la capa de presentación,
y mezclarla con el onboarding básico ampliaría innecesariamente el riesgo de este
corte.

Con B2a:

- RF-001 queda implementado y cubierto automáticamente.
- D-01 sigue abierto hasta las pruebas formales con proveedor real (PA-001/PA-002).
- D-10 sigue parcialmente abierto: cubre explicar la política de datos y mostrar
  proveedor/modelo predeterminados, pero no la edición de la ruta (B2b) ni la
  comprobación real de activación en Windows (Credential Manager con valor
  señuelo, pendiente de validación manual). El saludo con identidad propia y la
  propuesta de crear/describir el proyecto inicial (última cláusula de Producto
  §5.1) pertenecen a B3 (D-02, capacidad de proyecto utilizable) y no son una
  condición de cierre de D-10.
- PA-001 y PA-002 no se declaran superadas: exigen una credencial real y quedan
  bloqueadas hasta V8.3.

### B2b — Selección y persistencia de la ruta local de datos — FUSIONADA (PR #26, squash `2c60afc2652aadbf3aaa3e8672cd5a1f476e4ac4`)

Este corte dentro de B2 resuelve la ubicación de los datos **antes** de crear
directorios de datos, configurar el logging dependiente de la ruta, abrir
SQLite, ejecutar migraciones o construir repositorios/casos de uso de
persistencia:

- `BootstrapLocationStore` (`sirius.infrastructure.bootstrap_location_store`)
  guarda un puntero JSON mínimo de una única versión de esquema
  (`{"version": 1, "data_dir": "<ruta absoluta>"}`) en el directorio de
  configuración estable de Windows (`SiriusPaths.config_dir`, obtenido vía
  `platformdirs`), ahora fijo e independiente de `data_dir`
  (`resolve_paths(data_dir=...)`); escritura atómica (archivo temporal +
  `os.replace`), lectura segura y error explícito (`LocationFileCorruptedError`)
  ante corrupción, sin caer nunca en una base predeterminada en silencio.
  Separado de `settings.json`, SQLite, el almacén de secretos y la
  configuración del proveedor.
- `WindowsDataPathValidator` (`sirius.infrastructure.data_path_validator`)
  valida cada carpeta candidata: ruta absoluta, caracteres y nombres
  reservados de Windows, ausencia de un archivo ocupando el lugar de la
  carpeta, permiso de escritura probado con un archivo temporal real (nunca
  solo `os.access()`), espacios y Unicode, y reporta si la carpeta ya
  contiene una instalación Sirius (`sirius.db`) o está bajo OneDrive. No deja
  directorios parciales cuando la validación falla tras crear la carpeta.
- `DataLocationUseCase` (`sirius.application.data_location`) orquesta la
  resolución sin conocer SQLite, SQLAlchemy, migraciones ni platformdirs
  directamente: reutiliza silenciosamente una ubicación ya guardada (validada
  de nuevo antes de usarla), conserva sin pantalla de migración una
  instalación existente en la ruta predeterminada cuando todavía no hay
  archivo de ubicación, y solo pide una primera elección cuando ninguna de
  las dos aplica. Bloquea con `DataPathHasExistingInstallationError` una ruta
  personalizada que ya contiene datos de Sirius: este corte no adopta, mueve
  ni migra datos existentes fuera de la ruta predeterminada.
- `DataLocationWindow` (nueva ventana de presentación, independiente de
  `OnboardingWindow`) ofrece la ruta predeterminada ya seleccionada y una
  opción avanzada para elegir otra carpeta; distingue en su texto la ruta
  predeterminada, la personalizada, la advertencia de OneDrive (no
  bloqueante, exige confirmación explícita), el error de acceso y el caso de
  datos existentes no admitidos; se muestra también en modo recuperación
  cuando el archivo de ubicación está corrupto, y solo lo sobrescribe tras
  una elección nueva y válida.
- `sirius.main` resuelve la ubicación antes de cualquier paso dependiente de
  datos (`_build_first_window`) y solo entonces continúa, en la misma
  ejecución, con `initialize_persistence`, la composición y el onboarding de
  credencial de B2a (o la ventana principal si ya hay clave configurada); sin
  reiniciar Sirius y sin duplicar ventanas.

Cubierto con pruebas unitarias y de GUI (`tests/unit/test_paths.py`,
`tests/unit/test_data_path_validator.py`,
`tests/unit/test_bootstrap_location_store.py`,
`tests/unit/test_data_location_use_case.py`,
`tests/gui/test_data_location_window.py`, `tests/gui/test_app_bootstrap.py`),
siempre con dobles deterministas (`tmp_path`, `monkeypatch`, `qtbot`), sin
datos reales, sin clave real, sin Credential Manager real, sin OneDrive real
y sin red. La suite GUI específica de B2b se repitió 5 veces sin fallos.

Con B2b:

- La ruta predeterminada y una ruta personalizada quedan resueltas antes de
  SQLite, cubriendo la parte de D-10 relativa a la ruta de datos (Producto
  §5.1).
- La migración o adopción de datos existentes fuera de la ruta predeterminada
  queda explícitamente fuera de este corte y de D-10.
- D-10 sigue sin cerrarse por completo: falta la comprobación real de
  activación en Windows (Credential Manager con valor señuelo, pendiente de
  validación manual) y la validación manual de rutas reales de Windows
  (unidades de red, permisos reales, OneDrive real).
- PA-001 y PA-002 no se declaran superadas: exigen una credencial real y
  quedan bloqueadas hasta V8.3.
- No se inició B3.

Sin iniciar todavía Windows real ni proveedor real. Sin usar clave real ni red.

### B3a — Saludo inicial y creación utilizable del primer proyecto — FUSIONADA (PR #27, squash `882ab62416574e6a77c4714c6510565c1b670b1d`)

Primer corte dentro de B3: cubre parcialmente RF-014, RF-015 y el inicio de
RF-016, y la cláusula de Producto §5.1 sobre saludar con identidad propia y
proponer crear o describir el proyecto inicial. No completa B3 ni cierra D-02.

- `sirius.domain.project.is_configured()` distingue el placeholder de
  arranque (nombre y objetivo vacíos, sembrado por
  `get_or_create_active_project()` desde V3) de un proyecto realmente
  configurado por el usuario; es la única fuente de verdad para esa
  distinción, reutilizada por el caso de uso y por el arranque.
  `INITIAL_PROJECT_STATE`/`INITIAL_PROJECT_NEXT_STEP` son los valores
  mínimos y centralizados que RF-016 todavía no tenía definidos en ninguna
  fuente aprobada; aplicación, presentación y pruebas comparten esta única
  definición.
- `InitialProjectUseCase` (`sirius.application.initial_project`) consulta si
  el proyecto activo ya está configurado, lo expone de solo lectura y crea
  el primero completando transaccionalmente el placeholder existente (nunca
  insertando una segunda fila: la base ya impone una única fila con
  `is_active=1` mediante su índice único parcial), sin conocer SQLAlchemy ni
  SQLite. Rechaza con `InitialProjectAlreadyConfiguredError` un segundo
  intento cuando ya hay un proyecto configurado, comprobado antes de
  escribir nada y dejando el proyecto existente intacto (RF-015); rechaza
  con `InvalidInitialProjectDataError` un nombre u objetivo vacío tras
  recortar espacios, también antes de tocar el repositorio.
- `InitialProjectWindow` (nueva ventana de presentación, independiente de
  `OnboardingWindow` y de `MainWindow`) muestra un saludo determinista y
  centralizado (`GREETING_TEXT`, nunca generado por el proveedor, que
  reutiliza `sirius.domain.identity.INITIAL_IDENTITY_NAME` en vez de
  duplicar "Sirius" como constante) y solicita únicamente nombre y objetivo;
  foco inicial en el nombre, envío por botón o teclado, controles
  deshabilitados y reactivados de forma segura ante error, sin mostrar
  trazas internas, sin datos parciales al cerrar.
- `sirius.main` extiende la puerta de arranque existente: tras confirmarse
  la clave (ya existente o recién validada en la misma ejecución vía
  `OnboardingWindow`), `_build_post_key_window` consulta
  `InitialProjectUseCase.is_configured()` una única vez —compartida por
  ambos caminos que pueden llegar a "hay clave configurada", sin duplicar la
  comprobación— y solo entonces muestra `InitialProjectWindow`; al crear el
  proyecto se abre `ValidatedMainWindow` en la misma ejecución, sin
  reiniciar SQLite ni reconstruir el resto de repositorios.
- El proyecto configurado llega a `ContextBuilder` mediante el mecanismo ya
  existente (`ProjectRepository.get_active_project()`), sin ningún cambio en
  `sirius.application.context`: como `InitialProjectWindow` bloquea la
  apertura de `ValidatedMainWindow` hasta que el proyecto queda configurado,
  el placeholder vacío nunca llega a construirse un contexto real que se
  envíe al proveedor.

Cubierto con pruebas unitarias, de integración y de GUI
(`tests/unit/test_project_domain.py`,
`tests/unit/test_initial_project_use_case.py`,
`tests/integration/test_initial_project_persistence.py`,
`tests/gui/test_initial_project_window.py`, nuevos casos en
`tests/gui/test_app_bootstrap.py` incluyendo la cadena completa
DataLocationWindow → OnboardingWindow → InitialProjectWindow →
ValidatedMainWindow en una sola ejecución), siempre con dobles deterministas
o SQLite temporal, sin datos reales, sin clave real, sin red y sin
Credential Manager real. La suite GUI de B2a/B2b/B3a se repitió 5 veces sin
fallos.

Con B3a:

- RF-014 (crear con nombre y objetivo) queda implementado y cubierto
  automáticamente.
- RF-015 (impedir dos proyectos activos) queda protegido en la capa de
  aplicación y cubierto automáticamente.
- RF-016 queda cubierto solo en su parte inicial (estado y siguiente paso
  iniciales al crear); la actualización cotidiana, el resumen al retomar y
  el resto de RF-016 quedan pendientes.
- RF-017 y RF-018 no se abordan en este corte.
- D-02 queda parcialmente corregido: la creación del primer proyecto es
  utilizable desde la interfaz. Siguen pendientes de un corte posterior de
  B3: bloqueos del proyecto, decisiones relacionadas, completar y archivar
  conservando historial, y el resumen observable al retomar.
- PA-006 y PA-007 quedan preparadas/cubiertas automáticamente por esta
  implementación, pero no se declaran formalmente superadas (exigen
  evaluación conforme al Plan de Pruebas, no solo cobertura automática).
- No se implementó B3b, B4 ni B5. No se llamó a un proveedor real ni se usó
  una clave real.

### B3b — Continuidad observable del proyecto activo — FUSIONADA (PR #28, squash `a2f74df935f32835506c3228b328c2b9b6eec13b`)

Segundo corte dentro de B3. Texto aprobado verificado antes de implementar
(Definición de Producto Sirius 0.1 v0.2, S10): RF-016 "Conservar objetivo,
estado breve, decisiones, bloqueos y siguiente paso"; RF-017 "Recuperar el
proyecto al iniciar y resumirlo brevemente". Este corte cubre RF-016 en todo
salvo "decisiones" (que pertenece a B4, no implementado aquí) y cubre RF-017
completo. No completa B3 ni cierra D-02.

- Modelo y esquema: `Project.blockers: str` (dominio), columna `blockers`
  TEXT NOT NULL en `projects` (`ProjectModel`), migración Alembic
  `66951344e4b9` (revisa `0902e8217d75`) que añade la columna con
  `server_default=''` — no destructiva, conserva todo proyecto existente
  (id, nombre, objetivo, estado, siguiente paso, `is_active`), probada con
  Alembic real actualizando desde el head anterior y con `downgrade`.
  `ProjectRepository.update_project()` acepta `blockers: str | None = None`;
  `SqliteProjectRepository` lee/escribe la columna y persiste estado,
  bloqueos y siguiente paso en una única transacción por llamada. Cero o
  varios bloqueos se representan como texto libre separado por saltos de
  línea, sin tabla ni entidad `Blocker` independiente (decisión explícita de
  este corte).
- `ProjectContinuityUseCase` (`sirius.application.project_continuity`)
  consulta (`get_summary()`) y actualiza (`update()`) conjuntamente estado,
  bloqueos y siguiente paso del proyecto ya configurado, sin conocer
  SQLAlchemy ni SQLite. Nunca crea un proyecto como efecto de una lectura;
  rechaza con `ProjectNotConfiguredError` la ausencia de proyecto o el
  placeholder de arranque (nunca se devuelve como resumen válido); rechaza
  con `InvalidProjectContinuityDataError` un estado o siguiente paso vacío
  tras recortar espacios (bloqueos vacíos sí se permiten); normaliza
  bloqueos multilínea recortando espacios exteriores de cada línea y
  eliminando solo las líneas vacías del principio y el final, conservando el
  orden y los saltos de línea interiores intencionados; traduce cualquier
  fallo del repositorio a `ProjectContinuityError`, sin exponer nunca el
  tipo o el mensaje de la excepción original. Independiente de
  `InitialProjectUseCase` (responsabilidad distinta: primera configuración
  frente a continuidad de un proyecto ya configurado), ambos comparten la
  misma instancia de `ProjectRepository` construida una sola vez en
  `composition_root`.
- `ProjectContinuityWidget` (nuevo widget de presentación, no una pestaña ni
  ventana nueva) insertado por `MainWindow` encima del historial de mensajes
  en la pestaña "Conversación" existente: muestra nombre, objetivo, estado y
  bloqueos (`NO_BLOCKERS_TEXT`, "Sin bloqueos registrados.", centralizado)
  siempre que hay un proyecto configurado, y destaca el siguiente paso como
  "Ahora toca: …"; resumen determinista, local, visible al abrir, nunca
  generado por el proveedor, nunca persistido como mensaje ni añadido al
  historial. La acción "Actualizar proyecto" permite editar únicamente
  estado, bloqueos y siguiente paso (nombre y objetivo quedan de solo
  lectura en este corte) con "Guardar actualización"/"Cancelar": cancelar no
  escribe y recarga los valores persistidos; guardar actualiza los tres
  campos en una sola llamada, refresca el resumen y el "Ahora toca"
  inmediatamente, impide doble envío y, ante error, conserva lo escrito,
  reactiva los controles y muestra un mensaje seguro sin trazas ni nombres
  de excepciones. Si `MainWindow` se construye sin un proyecto configurado
  (caso defensivo; el flujo normal de `sirius.main` ya lo impide), el widget
  muestra un estado seguro ("Todavía no hay un proyecto configurado.") sin
  crear ningún proyecto y sin excepción sin traducir.
- `MainWindow` y `ValidatedMainWindow` reciben `ProjectContinuityUseCase`
  explícitamente (nuevo parámetro del constructor, sin exponer
  `ProjectRepository`); `composition_root` lo construye reutilizando el
  `ProjectRepository` ya existente (sin repositorio adicional) y lo añade a
  `ConversationDependencies`; `sirius.main` lo pasa a `ValidatedMainWindow`
  sin reiniciar SQLite ni reconstruir composición al actualizar.
- `render_instructions()` (`sirius.application.send_message`) añade
  `Nombre:` y `Bloqueos:` a la sección `# Proyecto activo` ya existente
  (formato: Nombre, Objetivo, Estado, Bloqueos, Siguiente paso), con
  "Bloqueos: Ninguno registrado." cuando no hay bloqueos; no incluye
  decisiones, recuerdos ni prioridades ficticias; no cambia la política de
  selección de contexto ni los límites de B6.

Cubierto con pruebas unitarias, de integración (incluida Alembic real, no
solo `Base.metadata.create_all`) y de GUI
(`tests/unit/test_project_domain.py` nuevos casos,
`tests/unit/test_project_continuity_use_case.py`,
`tests/unit/test_render_instructions.py`,
`tests/unit/test_composition_root_project_continuity.py`,
`tests/integration/test_sqlite_project_repository.py` nuevos casos,
`tests/integration/test_migrations.py` nuevos casos,
`tests/integration/test_send_message.py` nuevo caso,
`tests/gui/test_project_continuity_widget.py`,
`tests/gui/test_main_window.py` nuevos casos, `tests/gui/test_app_bootstrap.py`
nuevos casos incluyendo B3a en la misma ejecución y un reinicio simulado),
siempre con dobles deterministas o SQLite/Alembic reales sobre archivos
temporales, sin datos reales, sin clave real y sin red. La suite GUI de
B2a/B2b/B3a/B3b se repitió 5 veces sin fallos.

Con B3b:

- RF-016 queda cubierto en estado, bloqueos y siguiente paso; la parte de
  "decisiones" que también menciona su texto aprobado no se cubre aquí y
  pertenece a B4.
- RF-017 queda implementado y cubierto automáticamente (recuperación y
  resumen breve al retomar).
- D-02 sigue parcialmente corregido: quedan pendientes decisiones
  relacionadas (B4), completar y archivar el proyecto conservando historial,
  habilitar un proyecto posterior (solo permitido después de completar o
  archivar) y el resto de RF-018.
- PA-006 y PA-007 permanecen como en B3a (preparadas/cubiertas
  automáticamente, no formalmente superadas). PA-008 y PA-009 no se declaran
  superadas: PA-008 exige además recuperar una decisión registrada (B4, no
  implementado aquí) y PA-009 exige una recomendación evaluada del
  proveedor, no solo la presencia del dato en el contexto.
- No se implementó completar, archivar, un proyecto posterior, decisiones,
  B4, B5 ni B6. No se llamó a un proveedor real ni se usó una clave real.

### B3c — Ciclo de vida y versionado del proyecto — PR #29

Tercer y último corte dentro de B3. Texto aprobado verificado antes de
implementar (Definición de Producto Sirius 0.1 v0.2, S10): RF-018 "Marcarlo
completado sin borrar su historial". Solo se implementa COMPLETED: el texto
aprobado no menciona archivar, y RF-024 ("archivar") se aplica a
recuerdos/decisiones (B4), no al ciclo de vida propio de un proyecto —
ARCHIVED queda deliberadamente fuera de alcance de Sirius 0.1. Este corte
cierra D-02 en lo que respecta a B3 (decisiones relacionadas siguen
perteneciendo a B4).

- Dominio (`sirius.domain.project`, reescrito): `ProjectStatus` (`ACTIVE`,
  `COMPLETED`); `ProjectRevision` (instantánea inmutable y versionada de
  objetivo, estado, bloqueos y siguiente paso, con `source_event_id`
  reservado para el evento de origen que introducirá B4, siempre `None` por
  ahora); `Project` con `current_revision: ProjectRevision | None` (`None`
  únicamente en el placeholder de arranque nunca configurado) en vez de los
  campos planos de B3b — resuelto en persistencia a partir de
  `current_revision_id`, no expuesto en el dominio ni en la interfaz.
  `is_configured()` exige nombre no vacío, revisión presente y objetivo no
  vacío.
- Esquema (`ProjectModel`/`ProjectRevisionModel`) y migración Alembic
  `6f710ea6c2d2` (revisa `66951344e4b9`), no destructiva: añade `status`,
  `completed_at` y `current_revision_id` a `projects` (columnas planas
  `objective`, `current_state`, `blockers`, `next_step` se conservan solo
  por compatibilidad, ya no son la fuente autoritativa) y crea
  `project_revisions`. `current_revision_id` (campo mínimo exigido por
  SIRIUS-ARQ-0.1 S7.3, `NULL` solo en el placeholder sin configurar) es el
  único mecanismo autoritativo para determinar la revisión vigente de un
  proyecto — `project_revisions` no lleva ningún indicador `is_current` ni
  otra segunda fuente de verdad; el patrón `is_current` que sí usan
  `Identity`/`Memory` fue considerado y descartado aquí precisamente porque
  la arquitectura aprobada especifica `current_revision_id` para `project`.
  `current_revision_id` lleva una clave foránea física hacia
  `project_revisions.id` (verificado que `ALTER TABLE ... ADD COLUMN ...
  REFERENCES ...` y su posterior `DROP COLUMN` funcionan de forma directa en
  este proyecto, sin necesitar el modo por lotes de Alembic ni reconstruir
  la tabla); esa FK garantiza que la fila referenciada existe, pero no que
  pertenezca al mismo proyecto — `SqliteProjectRepository` valida eso en
  lectura y lo rechaza como corrupción (`InconsistentProjectRevisionError`)
  si no coincide. `upgrade()` clasifica cada fila existente como configurada
  o placeholder (mismo criterio que B3a/B3b) y, si está configurada, inserta
  su revisión 1 con los valores heredados y apunta `current_revision_id` a
  ella; `downgrade()` resincroniza las columnas planas desde la revisión
  vigente (vía `current_revision_id`) de cada proyecto antes de eliminar la
  tabla nueva (pérdida documentada y esperada de historial multi-revisión al
  bajar de versión, no un fallo silencioso). Probada con Alembic real: alta
  con relleno, alta de un placeholder sin revisión, alta de una fila ya
  inactiva como COMPLETED, y baja con resincronización.
- `ProjectRepository` (puerto, rediseñado): `get_active_project()`,
  `get_project(id)`, `list_project_revisions(id)`, `ensure_bootstrap_project()`
  (siembra el placeholder neutro solo si la tabla está vacía; nunca toca una
  fila existente, activa o cerrada — sustituye al antiguo
  `get_or_create_active_project()`), `create_project(...)` (reutiliza el
  placeholder sin configurar si existe, o abre una fila nueva; nunca
  reutiliza, reactiva ni sobrescribe un proyecto `COMPLETED`),
  `append_revision(...)` (nueva revisión sobre un proyecto `ACTIVE`
  configurado; nunca modifica una revisión anterior) y
  `complete_active_project(id)` (cambia `status`/`is_active`/`completed_at`
  en una sola transacción, sin tocar el contenido de la revisión actual).
  `SqliteProjectRepository` codifica los bloqueos como JSON
  (`blockers_json`, único lugar de serialización) y traduce un JSON inválido
  a `CorruptProjectRevisionError` en vez de convertirlo silenciosamente en
  una lista vacía.
- `application/project_errors.py` (nuevo): errores compartidos por
  `InitialProjectUseCase`, `ProjectContinuityUseCase` y el nuevo
  `ProjectLifecycleUseCase`, evitando que la misma semántica ("proyecto no
  configurado") divergiera entre los tres módulos.
  `InitialProjectUseCase.create_initial_project()` ahora es la misma
  operación tanto para el primer proyecto como para el siguiente tras
  completar el anterior (delega en `create_project()`, que decide
  internamente si reutiliza el placeholder o abre una fila nueva).
  `ProjectContinuityUseCase.update()` ya no sobrescribe el proyecto en
  sitio: añade una revisión nueva vía `append_revision()`, preservando el
  objetivo de la revisión actual (esta operación nunca lo cambia).
- `ProjectLifecycleUseCase` (nuevo, `sirius.application.project_lifecycle`):
  `complete_active_project()` completa el proyecto `ACTIVE` configurado
  conservando íntegramente su historial; rechaza con
  `ProjectNotConfiguredError` la ausencia de un proyecto activo configurado;
  nunca crea un proyecto siguiente (acción explícita y separada del
  usuario).
- `ContextBuilder.build()`: `Context.project` pasa a ser
  `Project | None` (SIRIUS-ARQ-0.1 S3, `LLMRequest.project_context: str |
  None`). Cero proyectos `ACTIVE` configurados — ausencia total, solo el
  placeholder, o todo proyecto existente `COMPLETED` — ya no es un fallo de
  arranque: `build()` nunca lanza `ContextAssemblyError` por esa causa
  únicamente, nunca recupera un proyecto `COMPLETED`, nunca crea un
  placeholder, y simplemente deja `context.project` en `None`. Identidad y
  conversación principal ausentes siguen lanzando ese mismo error, sin
  cambios. `render_instructions()` omite la sección "# Proyecto activo"
  íntegra cuando `context.project is None` — sin texto de relleno, sin
  proyecto inventado.
- `ProjectContinuityWidget`: nuevo botón "Completar proyecto" en la página
  de resumen, con diálogo de confirmación inyectable (mismo patrón que
  `confirm_restore` en `MainWindow`) antes de tocar el repositorio; solo tras
  confirmar llama a `ProjectLifecycleUseCase.complete_active_project()` y
  emite la señal `project_completed` (una sola vez, nunca antes de que el
  proyecto esté realmente completado). `MainWindow`/`ValidatedMainWindow`
  reciben `ProjectLifecycleUseCase` (nuevo parámetro del constructor) y
  reenvían la señal como `MainWindow.project_completed`.
- `sirius.main`: `_build_main_window()` conecta `project_completed` para
  cerrar la ventana principal y abrir `InitialProjectWindow` en el mismo
  proceso, reutilizando exactamente el mismo camino que ya usa el arranque
  cuando no hay proyecto configurado (`_build_initial_project_window`) — sin
  reiniciar Sirius. Esta transición inmediata nunca crea un proyecto por sí
  sola: `InitialProjectWindow` sigue exigiendo que el usuario escriba nombre
  y objetivo y pulse "Crear proyecto" antes de persistir nada, así que la
  garantía de que ningún proyecto se crea sin una acción explícita del
  usuario se mantiene igual que en B3a.

Cubierto con pruebas unitarias, de integración (incluida Alembic real) y de
GUI: `tests/unit/test_project_domain.py`, `tests/unit/test_render_instructions.py`
(reescritos sobre el nuevo dominio con revisión, incluida la ausencia de
proyecto);
`tests/unit/test_initial_project_use_case.py`,
`tests/unit/test_project_continuity_use_case.py` (reescritos sobre
`create_project`/`append_revision`); `tests/unit/test_project_lifecycle_use_case.py`
(nuevo); `tests/integration/test_sqlite_project_repository.py` (reescrito:
`ensure_bootstrap_project`, `create_project`, `append_revision`,
`complete_active_project`, `list_project_revisions`, corrupción de
`blockers_json`, puntero `current_revision_id`, FK física, revisión de otro
proyecto rechazada, rollback completo ante fallo entre inserción y
actualización del puntero); `tests/integration/test_migrations.py` (nuevos
casos de relleno con `current_revision_id` fijado, placeholder con puntero
`NULL`, y resincronización vía el puntero al bajar de versión);
`tests/integration/test_initial_project_persistence.py`,
`tests/integration/test_send_message.py`,
`tests/integration/test_persistence_bootstrap.py`,
`tests/integration/test_secret_leakage.py` (adaptados a la nueva forma del
proyecto); `tests/integration/test_context_builder.py` (reescrito: cero
proyectos activos, solo placeholder, y proyecto COMPLETED ya no fallan,
`context.project` queda en `None`); `tests/integration/test_backup_restore_project_lifecycle.py`
(nuevo); `tests/gui/test_project_continuity_widget.py`
(nuevos casos "Completar proyecto"), y el resto de la suite GUI adaptada a
la nueva firma de `MainWindow`/`ProjectRepository`. Suite GUI completa
repetida 5 veces sin fallos; `scripts/check.ps1` verde localmente (Ruff
format, Ruff lint, mypy estricto, 557 pytest).

Con B3c:

- RF-018 queda cubierto: completar sin borrar historial, con confirmación
  explícita, sin permitir un segundo proyecto activo simultáneo (RF-015 se
  mantiene) ni reactivar/editar/eliminar un proyecto ya cerrado.
- D-02 queda cerrado en lo que respecta a B3 (decisiones relacionadas siguen
  perteneciendo a B4, fuera de este corte).
- PA-006 y PA-007 permanecen como en B3a/B3b (preparadas/cubiertas
  automáticamente, no formalmente superadas). PA-008 y PA-009 siguen sin
  declararse superadas: PA-008 exige además recuperar una decisión
  registrada (B4) y PA-009 exige una recomendación evaluada del proveedor
  real.
- No se implementó ARCHIVED, decisiones, eventos, un historial general de
  proyectos ni panel de gestión, B4, B5 ni B6. No se llamó a un proveedor
  real ni se usó una clave real.

## Cierre de V8

V8 solo puede cerrarse cuando:

- PA-001 a PA-025 estén superadas;
- PA-E2E-01 esté superada;
- PS-01 a PS-07 estén evaluadas y aprobadas;
- SP-01 a SP-07 estén superadas;
- no existan defectos bloqueantes o altos;
- los defectos medios estén corregidos o aceptados explícitamente conforme al Plan de Pruebas;
- documentación, código y evidencia coincidan;
- el usuario apruebe explícitamente Sirius 0.1.

Al cerrar Sirius 0.1, este documento se congela como evidencia histórica.